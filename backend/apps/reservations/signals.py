"""Reservation signals that only persist transactional outbox events."""

from __future__ import annotations

import structlog
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.automations.models import OutboxEvent
from apps.automations.outbox import enqueue_outbox_event

from .models import Booking

logger = structlog.get_logger(__name__)


@receiver(pre_save, sender=Booking)
def cache_previous_booking_status(
    sender: type[Booking],
    instance: Booking,
    **kwargs: object,
) -> None:
    """Keep track of prior status before saving."""
    _ = sender, kwargs
    previous = (
        Booking.objects.filter(pk=instance.pk).values("status").first()
        if instance.pk
        else None
    )
    instance._previous_status = previous["status"] if previous else None


@receiver(post_save, sender=Booking)
def booking_post_save(
    sender: type[Booking],
    instance: Booking,
    created: bool,
    **kwargs: object,
) -> None:
    """Persist external side effects without executing them in the request."""
    _ = sender, kwargs
    previous_status = getattr(instance, "_previous_status", None)
    became_confirmed = instance.status == Booking.Status.CONFIRMED and (
        created or previous_status != Booking.Status.CONFIRMED
    )
    if not became_confirmed:
        return

    logger.info(
        "booking_confirmed",
        booking_id=str(instance.id),
        confirmation_code=instance.confirmation_code,
    )
    enqueue_outbox_event(
        event_key=f"booking-email:{instance.id}:confirmed",
        event_type=OutboxEvent.EventType.BOOKING_EMAIL,
        payload={"booking_id": str(instance.id), "template": "booking_confirmation"},
    )
