"""Knowledge ingestion service."""

from __future__ import annotations

from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from apps.ai.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from apps.ai.services.embedding_service import EmbeddingService
from apps.ai.services.vector_store import VectorStore

from .chunkers import chunk_text


class KnowledgeIngestionService:
    """Create or refresh knowledge documents and chunks."""

    def __init__(self) -> None:
        """Create helper services."""
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

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
        self.vector_store.delete_chunk_embeddings_for_document(document.id)
        document.chunks.all().delete()
        chunk_payloads = chunk_text(title=title, content=content)
        embedding_inputs = [
            (
                f"document_title: {title}\n"
                f"section: {chunk['section']}\n"
                f"language: {language}\n"
                f"channel: {channel}\n"
                f"content: {chunk['content']}"
            )
            for chunk in chunk_payloads
        ]
        embedding_result = self.embedding_service.embed_texts(embedding_inputs)
        vectors = embedding_result.vectors if embedding_result is not None else []
        embedding_model = embedding_result.model if embedding_result is not None else ""

        for index, chunk in enumerate(chunk_payloads):
            embedding = vectors[index] if index < len(vectors) else []
            instance = KnowledgeChunk.objects.create(
                document=document,
                chunk_index=index,
                section=str(chunk["section"]),
                content=str(chunk["content"]),
                token_count=int(chunk["token_count"]),
                content_hash=str(chunk["content_hash"]),
                embedding=embedding,
                embedding_model=embedding_model,
                metadata={},
            )
            if embedding:
                self.vector_store.upsert_chunk_embedding(chunk_id=instance.id, embedding=embedding)
        source.last_synced_at = timezone.now()
        source.save(update_fields=["last_synced_at", "updated_at"])
        return document
