"""Knowledge ingestion service."""

from __future__ import annotations

from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from apps.ai.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

from .chunkers import chunk_text


class KnowledgeIngestionService:
    """Create or refresh knowledge documents and chunks."""

    @transaction.atomic
    def upsert_document(
        self,
        *,
        source: KnowledgeSource,
        external_id: str,
        title: str,
        content: str,
        channel: str = KnowledgeDocument.Channel.PUBLIC,
        language: str = "es-AR",
        metadata: dict[str, object] | None = None,
    ) -> KnowledgeDocument:
        """Create or update a document and replace its active chunks."""
        checksum = sha256(content.encode("utf-8")).hexdigest()
        document, _ = KnowledgeDocument.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults={
                "title": title,
                "language": language,
                "channel": channel,
                "checksum": checksum,
                "metadata": metadata or {},
                "is_active": True,
                "published_at": timezone.now(),
            },
        )
        document.chunks.all().delete()
        for index, chunk in enumerate(chunk_text(title=title, content=content)):
            KnowledgeChunk.objects.create(
                document=document,
                chunk_index=index,
                section=str(chunk["section"]),
                content=str(chunk["content"]),
                token_count=int(chunk["token_count"]),
                content_hash=str(chunk["content_hash"]),
                embedding=[],
                embedding_model="",
                metadata={},
            )
        source.last_synced_at = timezone.now()
        source.save(update_fields=["last_synced_at", "updated_at"])
        return document
