"""Tests for embeddings, ingestion, and reindexing."""

from __future__ import annotations

import io
import sys
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from apps.ai.models import KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.ai.services.embedding_service import EmbeddingBatchResult, EmbeddingService


class _FakeEmbeddingRecord:
    """Minimal embedding record returned by the OpenAI embeddings API."""

    def __init__(self, embedding: list[float]) -> None:
        """Store one embedding vector."""
        self.embedding = embedding


class _FakeEmbeddingsAPI:
    """Minimal fake embeddings API."""

    def create(self, **kwargs: object) -> object:
        """Return a fake batch embedding response."""
        inputs = list(kwargs["input"])
        return SimpleNamespace(
            data=[
                _FakeEmbeddingRecord([float(index + 1), float(len(text))])
                for index, text in enumerate(inputs)
            ]
        )


class _FakeOpenAIClient:
    """Minimal fake OpenAI client for embeddings tests."""

    def __init__(self, *, api_key: str) -> None:
        """Expose the fake embeddings namespace."""
        del api_key
        self.embeddings = _FakeEmbeddingsAPI()


@pytest.mark.django_db
def test_embedding_service_returns_vectors_with_mocked_openai(settings, monkeypatch) -> None:
    """Embedding service should normalize OpenAI embedding responses."""
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAIClient))

    result = EmbeddingService().embed_texts(["hola mundo", "retiro en bodega"])

    assert result is not None
    assert result.used_remote is True
    assert result.model == settings.AI_EMBEDDING_MODEL
    assert len(result.vectors) == 2
    assert result.vectors[0][0] == 1.0


@pytest.mark.django_db
def test_knowledge_ingestion_persists_embeddings_and_vector_upserts(monkeypatch) -> None:
    """Ingestion should store returned embeddings and trigger vector upserts."""
    source = KnowledgeSource.objects.create(
        name="Embeddings KB",
        source_type=KnowledgeSource.SourceType.MANUAL,
        uri="seed://embeddings",
    )
    service = KnowledgeIngestionService()
    vector_calls: list[tuple[int, list[float]]] = []

    monkeypatch.setattr(
        service.embedding_service,
        "embed_texts",
        lambda texts: EmbeddingBatchResult(
            model="mock-embed-model",
            vectors=[[0.1, 0.2] for _ in texts],
            used_remote=True,
        ),
    )
    monkeypatch.setattr(
        service.vector_store,
        "upsert_chunk_embedding",
        lambda *, chunk_id, embedding: vector_calls.append((chunk_id, embedding)),
    )

    document = service.upsert_document(
        source=source,
        external_id="embeddings-doc",
        title="Embeddings Document",
        content="Primer párrafo.\nSegundo párrafo.",
    )

    chunks = list(document.chunks.order_by("chunk_index"))
    assert len(chunks) >= 1
    assert chunks[0].embedding == [0.1, 0.2]
    assert chunks[0].embedding_model == "mock-embed-model"
    assert len(vector_calls) == len(chunks)


@pytest.mark.django_db
def test_reindex_ai_knowledge_command_refreshes_active_documents(monkeypatch) -> None:
    """Reindex command should rebuild active documents through the ingestion service."""
    source = KnowledgeSource.objects.create(
        name="Reindex KB",
        source_type=KnowledgeSource.SourceType.MANUAL,
        uri="seed://reindex",
    )
    service = KnowledgeIngestionService()
    monkeypatch.setattr(service.embedding_service, "embed_texts", lambda texts: None)
    monkeypatch.setattr(service.vector_store, "upsert_chunk_embedding", lambda **kwargs: None)
    document = service.upsert_document(
        source=source,
        external_id="reindex-doc",
        title="Reindex Document",
        content="Contenido inicial para reindexar.",
    )
    del document

    captured: list[tuple[str, str]] = []

    original_upsert = KnowledgeIngestionService.upsert_document

    def spying_upsert(self: KnowledgeIngestionService, **kwargs: object):
        """Capture reindex calls while preserving the original behavior."""
        captured.append((str(kwargs["external_id"]), str(kwargs["title"])))
        monkeypatch.setattr(self.embedding_service, "embed_texts", lambda texts: None)
        monkeypatch.setattr(self.vector_store, "upsert_chunk_embedding", lambda **inner_kwargs: None)
        return original_upsert(self, **kwargs)

    monkeypatch.setattr(KnowledgeIngestionService, "upsert_document", spying_upsert)

    stdout = io.StringIO()
    call_command("reindex_ai_knowledge", stdout=stdout)

    assert ("reindex-doc", "Reindex Document") in captured
    assert "Reindexed 1 AI knowledge document" in stdout.getvalue()
