"""Simple hybrid-ish retrieval over the knowledge tables."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q

from apps.ai.models import KnowledgeChunk
from apps.ai.services.embedding_service import EmbeddingService
from apps.ai.services.vector_store import VectorSearchResult, VectorStore

TOKEN_RE = re.compile(r"[a-z0-9áéíóúñü]+", re.IGNORECASE)


@dataclass(slots=True)
class RetrievedChunk:
    """Normalized retrieval result."""

    chunk_id: int
    document_id: int
    document_title: str
    section: str
    content: str
    score: int

    @property
    def citation(self) -> dict[str, object]:
        """Return a compact citation object for responses."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "section": self.section,
        }


class KnowledgeRetriever:
    """Query the knowledge base using lexical search and optional pgvector search."""

    def __init__(self) -> None:
        """Create helper services."""
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def search(
        self,
        query: str,
        *,
        channel: str = "public",
        limit: int | None = None,
    ) -> list[RetrievedChunk]:
        """Return the best matching chunks for the given query."""
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        lexical_results = self._lexical_search(
            normalized_query=normalized_query,
            channel=channel,
        )
        query_embedding = self.embedding_service.embed_query(query)
        semantic_results = (
            self.vector_store.search(
                query_embedding=query_embedding,
                channel=channel,
                limit=max(limit or settings.AI_MAX_KNOWLEDGE_RESULTS, 12),
            )
            if query_embedding
            else []
        )
        fused_results = self._fuse_results(lexical_results, semantic_results)
        return fused_results[: limit or settings.AI_MAX_KNOWLEDGE_RESULTS]

    def _lexical_search(
        self,
        *,
        normalized_query: str,
        channel: str,
    ) -> list[RetrievedChunk]:
        """Return lexical matches for a normalized query."""
        terms = [term for term in TOKEN_RE.findall(normalized_query) if len(term) > 2]
        filters = Q(document__is_active=True, document__source__is_active=True)
        if channel:
            filters &= Q(document__channel=channel)
        if terms:
            term_filter = Q()
            for term in terms:
                term_filter |= Q(content__icontains=term) | Q(section__icontains=term)
            filters &= term_filter

        chunks = (
            KnowledgeChunk.objects.select_related("document")
            .filter(filters)
            .order_by("document_id", "chunk_index")[:200]
        )
        results = [self._score_chunk(chunk, terms or [normalized_query]) for chunk in chunks]
        results = [result for result in results if result.score > 0]
        results.sort(key=lambda item: item.score, reverse=True)
        return results

    def _score_chunk(self, chunk: KnowledgeChunk, terms: Iterable[str]) -> RetrievedChunk:
        """Assign a simple lexical relevance score to a chunk."""
        content_lower = chunk.content.lower()
        section_lower = chunk.section.lower()
        score = 0
        for term in terms:
            score += content_lower.count(term)
            score += section_lower.count(term) * 2
            if chunk.document.title.lower().find(term) >= 0:
                score += 3
        return RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            section=chunk.section,
            content=chunk.content,
            score=score,
        )

    def _fuse_results(
        self,
        lexical_results: list[RetrievedChunk],
        semantic_results: list[VectorSearchResult],
    ) -> list[RetrievedChunk]:
        """Fuse lexical and semantic lists using reciprocal rank style scoring."""
        combined: dict[int, RetrievedChunk] = {}
        scores: dict[int, float] = {}

        for rank, item in enumerate(lexical_results):
            combined[item.chunk_id] = item
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + (1.0 / (50 + rank + 1))

        for rank, item in enumerate(semantic_results):
            if item.chunk_id not in combined:
                combined[item.chunk_id] = RetrievedChunk(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_title=item.document_title,
                    section=item.section,
                    content=item.content,
                    score=0,
                )
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + (1.0 / (50 + rank + 1))

        ranked = sorted(
            combined.values(),
            key=lambda item: scores.get(item.chunk_id, 0.0),
            reverse=True,
        )
        return ranked
