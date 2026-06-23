"""Workers for durable transactional outbox events."""

from __future__ import annotations

from datetime import timedelta

import structlog
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.fulfillment import PermanentFulfillmentError
from apps.orders.models import Order

from ..models import OutboxEvent

logger = structlog.get_logger(__name__)


@shared_task
def process_outbox_event(event_id: str) -> dict[str, object]:
    """Claim and execute one durable side effect."""
    with transaction.atomic():
        event = OutboxEvent.objects.select_for_update().get(pk=event_id)
        if event.status == OutboxEvent.Status.COMPLETED:
            return {"event_id": event_id, "status": "already_completed"}
        if event.status == OutboxEvent.Status.PROCESSING:
            return {"event_id": event_id, "status": "already_processing"}
        if event.available_at > timezone.now():
            return {"event_id": event_id, "status": "not_ready"}
        event.status = OutboxEvent.Status.PROCESSING
        event.attempts += 1
        event.save(update_fields=["status", "attempts", "updated_at"])

    try:
        _execute_event(event)
    except PermanentFulfillmentError as exc:
        _mark_failed(event, exc)
    except Exception as exc:  # external services are retried by the dispatcher
        _mark_for_retry(event, exc)
    else:
        OutboxEvent.objects.filter(pk=event.pk).update(
            status=OutboxEvent.Status.COMPLETED,
            processed_at=timezone.now(),
            last_error="",
            updated_at=timezone.now(),
        )
    event.refresh_from_db()
    return {"event_id": event_id, "status": event.status, "attempts": event.attempts}


def _execute_event(event: OutboxEvent) -> None:
    order_id = str(event.payload.get("order_id") or "")
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    if event.event_type == OutboxEvent.EventType.ORDER_EMAIL:
        from apps.orders.fulfillment import send_order_email

        send_order_email(order, template=str(event.payload.get("template") or ""))
        return
    if event.event_type == OutboxEvent.EventType.ANDREANI_FULFILLMENT:
        from apps.orders.fulfillment import sync_andreani_shipping_order

        sync_andreani_shipping_order(order, retry_failed=event.attempts > 1)
        return
    raise PermanentFulfillmentError(f"Tipo de evento desconocido: {event.event_type}")


def _mark_failed(event: OutboxEvent, exc: Exception) -> None:
    OutboxEvent.objects.filter(pk=event.pk).update(
        status=OutboxEvent.Status.FAILED,
        last_error=str(exc),
        updated_at=timezone.now(),
    )
    logger.error("outbox_event_failed", event_id=str(event.id), error=str(exc))


def _mark_for_retry(event: OutboxEvent, exc: Exception) -> None:
    max_attempts = settings.OUTBOX_MAX_ATTEMPTS
    if event.attempts >= max_attempts:
        _mark_failed(event, exc)
        return
    delay_seconds = min(60 * (2 ** max(event.attempts - 1, 0)), 3600)
    OutboxEvent.objects.filter(pk=event.pk).update(
        status=OutboxEvent.Status.PENDING,
        available_at=timezone.now() + timedelta(seconds=delay_seconds),
        last_error=str(exc),
        updated_at=timezone.now(),
    )
    logger.warning(
        "outbox_event_retry_scheduled",
        event_id=str(event.id),
        attempts=event.attempts,
        delay_seconds=delay_seconds,
        error=str(exc),
    )


@shared_task
def dispatch_pending_outbox_events() -> dict[str, int]:
    """Dispatch ready events and recover workers that died while processing."""
    stale_before = timezone.now() - timedelta(minutes=settings.OUTBOX_PROCESSING_TIMEOUT_MINUTES)
    OutboxEvent.objects.filter(
        status=OutboxEvent.Status.PROCESSING,
        updated_at__lt=stale_before,
    ).update(status=OutboxEvent.Status.PENDING, available_at=timezone.now())

    event_ids = list(
        OutboxEvent.objects.filter(
            status=OutboxEvent.Status.PENDING,
            available_at__lte=timezone.now(),
        )
        .order_by("available_at")
        .values_list("id", flat=True)[: settings.OUTBOX_DISPATCH_BATCH_SIZE]
    )
    for event_id in event_ids:
        process_outbox_event.delay(str(event_id))
    return {"dispatched": len(event_ids)}
