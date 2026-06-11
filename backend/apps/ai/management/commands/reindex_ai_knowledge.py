"""Reindex AI knowledge documents and refresh embeddings."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ai.models import KnowledgeDocument
from apps.ai.rag.ingest import KnowledgeIngestionService


class Command(BaseCommand):
    """Rebuild AI knowledge chunks and embeddings from stored documents."""

    help = "Reindex AI knowledge chunks and embeddings."

    def handle(self, *args: object, **options: object) -> None:
        """Refresh chunks and embeddings for all active knowledge documents."""
        del args, options
        service = KnowledgeIngestionService()
        documents = KnowledgeDocument.objects.select_related("source").filter(is_active=True)
        reindexed = 0
        for document in documents:
            combined_content = "\n".join(
                document.chunks.order_by("chunk_index").values_list("content", flat=True)
            )
            if not combined_content.strip():
                continue
            service.upsert_document(
                source=document.source,
                external_id=document.external_id,
                title=document.title,
                content=combined_content,
                channel=document.channel,
                language=document.language,
                metadata=document.metadata,
            )
            reindexed += 1
        self.stdout.write(self.style.SUCCESS(f"Reindexed {reindexed} AI knowledge document(s)."))
