"""Simple hybrid-ish retrieval over the knowledge tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.db.models import Q

from apps.ai.models import KnowledgeChunk


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
    """Query the knowledge base without requiring vector infra at bootstrap time."""

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

        terms = [term for term in normalized_query.split() if len(term) > 2]
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
        return results[: limit or settings.AI_MAX_KNOWLEDGE_RESULTS]

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
