"""Optional pgvector-backed store for semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import connection


@dataclass(slots=True)
class VectorSearchResult:
    """Normalized semantic search result."""

    chunk_id: int
    document_id: int
    document_title: str
    section: str
    content: str
    score: float


class VectorStore:
    """Persist and query semantic vectors when pgvector is available."""

    _extension_checked = False
    _extension_available = False

    def is_available(self) -> bool:
        """Return True when the current DB can serve pgvector queries."""
        if not settings.AI_ENABLE_PGVECTOR:
            return False
        if connection.vendor != "postgresql":
            return False
        if self.__class__._extension_checked:
            return self.__class__._extension_available

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1")
                self.__class__._extension_available = cursor.fetchone() is not None
        except Exception:
            self.__class__._extension_available = False

        self.__class__._extension_checked = True
        return self.__class__._extension_available

    def upsert_chunk_embedding(
        self,
        *,
        chunk_id: int,
        embedding: list[float],
    ) -> None:
        """Persist an embedding for a knowledge chunk."""
        if not embedding or not self.is_available():
            return
        vector_value = self._vector_literal(embedding)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_knowledgechunk_embedding (chunk_id, embedding)
                VALUES (%s, %s::vector)
                ON CONFLICT (chunk_id)
                DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                [chunk_id, vector_value],
            )

    def delete_chunk_embeddings_for_document(self, document_id: int) -> None:
        """Delete embeddings for all chunks attached to a document."""
        if not self.is_available():
            return
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM ai_knowledgechunk_embedding
                WHERE chunk_id IN (
                    SELECT id FROM ai_knowledgechunk WHERE document_id = %s
                )
                """,
                [document_id],
            )

    def search(
        self,
        *,
        query_embedding: list[float],
        channel: str,
        limit: int,
    ) -> list[VectorSearchResult]:
        """Run a semantic nearest-neighbor query over knowledge chunks."""
        if not query_embedding or not self.is_available():
            return []

        vector_value = self._vector_literal(query_embedding)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    chunk.id,
                    document.id,
                    document.title,
                    chunk.section,
                    chunk.content,
                    1 - (embedding.embedding <=> %s::vector) AS similarity
                FROM ai_knowledgechunk_embedding AS embedding
                JOIN ai_knowledgechunk AS chunk
                    ON chunk.id = embedding.chunk_id
                JOIN ai_knowledgedocument AS document
                    ON document.id = chunk.document_id
                JOIN ai_knowledgesource AS source
                    ON source.id = document.source_id
                WHERE document.is_active = TRUE
                  AND source.is_active = TRUE
                  AND document.channel = %s
                ORDER BY embedding.embedding <=> %s::vector
                LIMIT %s
                """,
                [vector_value, channel, vector_value, limit],
            )
            rows = cursor.fetchall()

        return [
            VectorSearchResult(
                chunk_id=row[0],
                document_id=row[1],
                document_title=row[2],
                section=row[3] or "",
                content=row[4],
                score=float(row[5] or 0.0),
            )
            for row in rows
        ]

    def _vector_literal(self, embedding: list[float]) -> str:
        """Render a vector literal accepted by pgvector."""
        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
