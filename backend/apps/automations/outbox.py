"""Transactional outbox enqueue helpers."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import OutboxEvent


def enqueue_outbox_event(
    *,
    event_key: str,
    event_type: str,
    payload: dict[str, object],
    revive: bool = False,
) -> OutboxEvent:
    """Persist one idempotent event and schedule it only after commit."""
    event, created = OutboxEvent.objects.get_or_create(
        event_key=event_key,
        defaults={"event_type": event_type, "payload": payload},
    )
    if revive and not created and event.status != OutboxEvent.Status.PENDING:
        event.status = OutboxEvent.Status.PENDING
        event.payload = payload
        event.available_at = timezone.now()
        event.processed_at = None
        event.last_error = ""
        event.save(
            update_fields=[
                "status",
                "payload",
                "available_at",
                "processed_at",
                "last_error",
                "updated_at",
            ]
        )

    if created or revive:
        transaction.on_commit(lambda: _dispatch_event(str(event.id)))
    return event


def _dispatch_event(event_id: str) -> None:
    """Import lazily to avoid app-loading cycles."""
    from .tasks.outbox_tasks import process_outbox_event

    process_outbox_event.delay(event_id)
