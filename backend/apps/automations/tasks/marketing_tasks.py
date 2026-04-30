"""Marketing automation tasks."""

from __future__ import annotations

from datetime import timedelta

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.authentication.models import CustomUser
from apps.notifications.email import EmailService
from apps.orders.models import PromoCode

logger = structlog.get_logger(__name__)


@shared_task
def send_birthday_discounts() -> dict[str, int]:
    """Send birthday promo codes to subscribed customers."""
    today = timezone.localdate()
    current_year = today.year

    birthday_users = CustomUser.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day,
        newsletter_subscribed=True,
        is_active=True,
    ).exclude(birthday_discount_sent_year=current_year)

    sent = 0
    for user in birthday_users:
        code = PromoCode.objects.create(
            code=f"CUMPLE-{user.id.hex[:8].upper()}-{current_year}",
            discount_type=PromoCode.DiscountType.PERCENTAGE,
            discount_value=15,
            min_order_amount=5000,
            max_uses=1,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=True,
        )
        EmailService.send_transactional(
            to=user.email,
            template="birthday_discount",
            context={
                "first_name": user.first_name,
                "discount_percentage": 15,
                "promo_code": code.code,
                "expiry_date": code.valid_until.strftime("%d/%m/%Y"),
                "shop_url": f"{settings.FRONTEND_URL}/vinos?promo={code.code}",
            },
        )
        user.birthday_discount_sent_year = current_year
        user.save(update_fields=["birthday_discount_sent_year"])
        sent += 1

    logger.info("birthday_discounts_sent", count=sent, date=str(today))
    return {"birthday_emails_sent": sent}
