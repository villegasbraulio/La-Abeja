"""Embedding helpers for the AI knowledge layer."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(slots=True)
class EmbeddingBatchResult:
    """Normalized embedding response."""

    model: str
    vectors: list[list[float]]
    used_remote: bool


class EmbeddingService:
    """Generate embeddings for documents and queries."""

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult | None:
        """Embed a batch of texts when OpenAI is configured."""
        cleaned = [text.strip() for text in texts if text.strip()]
        if not cleaned:
            return EmbeddingBatchResult(model="none", vectors=[], used_remote=False)
        provider_name = str(getattr(settings, "AI_LLM_PROVIDER", "openai")).strip().lower()
        if provider_name == "groq":
            return None
        if not settings.OPENAI_API_KEY or not settings.AI_USE_LLM:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                model=settings.AI_EMBEDDING_MODEL,
                input=cleaned,
                dimensions=settings.AI_PGVECTOR_DIMENSIONS,
            )
        except Exception:
            return None

        return EmbeddingBatchResult(
            model=settings.AI_EMBEDDING_MODEL,
            vectors=[list(item.embedding) for item in response.data],
            used_remote=True,
        )

    def embed_query(self, text: str) -> list[float] | None:
        """Embed a single query string."""
        result = self.embed_texts([text])
        if result is None or not result.vectors:
            return None
        return result.vectors[0]
