"""Background tasks for AI knowledge operations."""

from __future__ import annotations

from celery import shared_task

from apps.ai.models import KnowledgeSource


@shared_task
def sync_knowledge_source(source_id: int) -> dict[str, object]:
    """Mark a knowledge source sync request as accepted."""
    source = KnowledgeSource.objects.get(id=source_id)
    return {
        "source_id": source.id,
        "source_name": source.name,
        "status": "accepted",
    }
