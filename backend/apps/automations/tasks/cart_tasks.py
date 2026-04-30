"""Cart automation tasks."""

from __future__ import annotations

from datetime import timedelta

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications.email import EmailService
from apps.orders.models import Cart

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_abandoned_carts(self) -> dict[str, int]:
    """Queue recovery emails for carts inactive for more than one hour."""
    threshold = timezone.now() - timedelta(hours=1)
    abandoned = Cart.objects.filter(
        user__isnull=False,
        last_activity_at__lte=threshold,
        abandon_reminder_sent=False,
    ).prefetch_related("items__wine__varietal", "user")

    emails_sent = 0
    processed = 0
    for cart in abandoned:
        if cart.items.exists():
            processed += 1
            send_abandoned_cart_email(str(cart.id))
            cart.abandon_reminder_sent = True
            cart.save(update_fields=["abandon_reminder_sent"])
            emails_sent += 1

    logger.info("abandoned_cart_check", processed=processed, emails_sent=emails_sent)
    return {"processed": processed, "emails_sent": emails_sent}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_abandoned_cart_email(self, cart_id: str) -> bool:
    """Send a personalized abandoned cart email."""
    try:
        cart = (
            Cart.objects.select_related("user")
            .prefetch_related("items__wine__varietal")
            .get(id=cart_id)
        )
        if cart.user is None:
            return False
        cart_items = [
            {
                "name": item.wine.name,
                "varietal": item.wine.varietal.name,
                "vintage": item.wine.vintage_year,
                "quantity": item.quantity,
                "price": str(item.unit_price),
            }
            for item in cart.items.all()
        ]
        EmailService.send_transactional(
            to=cart.user.email,
            template="abandoned_cart",
            context={
                "first_name": cart.user.first_name,
                "cart_items": cart_items,
                "cart_total": str(cart.total),
                "recovery_url": f"{settings.FRONTEND_URL}/carrito?recover={cart.id}",
            },
        )
        return True
    except Exception as exc:
        logger.error("abandoned_cart_email_failed", cart_id=cart_id, error=str(exc))
        raise self.retry(exc=exc) from exc
