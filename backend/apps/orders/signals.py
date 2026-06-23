"""Order signals that only persist transactional outbox events."""

from __future__ import annotations

import structlog
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.automations.models import OutboxEvent
from apps.automations.outbox import enqueue_outbox_event

from .models import Order

logger = structlog.get_logger(__name__)


@receiver(pre_save, sender=Order)
def cache_previous_order_status(
    sender: type[Order],
    instance: Order,
    **kwargs: object,
) -> None:
    """Keep track of prior values before saving."""
    _ = sender, kwargs
    previous = (
        Order.objects.filter(pk=instance.pk).values("status", "tracking_number").first()
        if instance.pk
        else None
    )
    instance._previous_status = previous["status"] if previous else None
    instance._previous_tracking_number = previous["tracking_number"] if previous else ""


@receiver(post_save, sender=Order)
def order_post_save(
    sender: type[Order],
    instance: Order,
    created: bool,
    **kwargs: object,
) -> None:
    """Persist external side effects without executing them in the request."""
    _ = sender, kwargs
    if created:
        return

    previous_status = getattr(instance, "_previous_status", None)
    previous_tracking_number = getattr(instance, "_previous_tracking_number", "")
    if previous_status and previous_status != instance.status:
        logger.info("order_status_changed", order_id=str(instance.id), status=instance.status)
        enqueue_outbox_event(
            event_key=f"order-email:{instance.id}:status:{instance.status}",
            event_type=OutboxEvent.EventType.ORDER_EMAIL,
            payload={"order_id": str(instance.id), "template": "order_status_update"},
        )
        if (
            instance.status in {Order.Status.PAID, Order.Status.PREPARING}
            and instance.shipping_method != Order.ShippingMethod.PICKUP
        ):
            enqueue_outbox_event(
                event_key=f"andreani-fulfillment:{instance.id}",
                event_type=OutboxEvent.EventType.ANDREANI_FULFILLMENT,
                payload={"order_id": str(instance.id)},
            )

    if instance.tracking_number and previous_tracking_number != instance.tracking_number:
        logger.info(
            "order_tracking_updated",
            order_id=str(instance.id),
            tracking_number=instance.tracking_number,
        )
        enqueue_outbox_event(
            event_key=f"order-email:{instance.id}:tracking:{instance.tracking_number}",
            event_type=OutboxEvent.EventType.ORDER_EMAIL,
            payload={"order_id": str(instance.id), "template": "order_tracking_update"},
        )
