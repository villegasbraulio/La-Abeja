"""Edge-case coverage for lexical and semantic retrieval."""

from __future__ import annotations

import pytest

from apps.ai.models import KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.ai.rag.retriever import KnowledgeRetriever
from apps.ai.services.vector_store import VectorSearchResult


@pytest.mark.django_db
def test_retriever_returns_empty_list_for_blank_queries() -> None:
    """Blank queries should not hit the DB or return noisy matches."""
    assert KnowledgeRetriever().search("   ") == []


@pytest.mark.django_db
def test_retriever_normalizes_punctuation_in_lexical_queries() -> None:
    """Lexical search should still match user queries with punctuation noise."""
    source = KnowledgeSource.objects.create(
        name="FAQ Eval",
        source_type=KnowledgeSource.SourceType.FAQ,
        uri="seed://faq-eval",
    )
    KnowledgeIngestionService().upsert_document(
        source=source,
        external_id="pickup-faq",
        title="Retiro en bodega",
        content="El retiro en bodega se coordina luego de la confirmacion.",
    )

    results = KnowledgeRetriever().search("retiro, en bodega???", channel="public")

    assert results
    assert results[0].document_title == "Retiro en bodega"


@pytest.mark.django_db
def test_retriever_respects_public_vs_internal_channels() -> None:
    """Public callers should not see internal-only knowledge chunks."""
    source = KnowledgeSource.objects.create(
        name="Policies Eval",
        source_type=KnowledgeSource.SourceType.MANUAL,
        uri="seed://policies-eval",
    )
    ingestion = KnowledgeIngestionService()
    ingestion.upsert_document(
        source=source,
        external_id="public-doc",
        title="Envios publicos",
        content="La cobertura publica prioritaria es Cuyo y AMBA.",
        channel="public",
    )
    ingestion.upsert_document(
        source=source,
        external_id="internal-doc",
        title="Playbook interno",
        content="Escalar reclamos urgentes al equipo de operaciones.",
        channel="internal",
    )

    public_results = KnowledgeRetriever().search("reclamos urgentes", channel="public")
    internal_results = KnowledgeRetriever().search("reclamos urgentes", channel="internal")

    assert public_results == []
    assert internal_results
    assert internal_results[0].document_title == "Playbook interno"


@pytest.mark.django_db
def test_retriever_can_return_semantic_only_results(monkeypatch) -> None:
    """Semantic fusion should surface chunks even when lexical search misses them."""
    source = KnowledgeSource.objects.create(
        name="Semantic Eval",
        source_type=KnowledgeSource.SourceType.MANUAL,
        uri="seed://semantic-eval",
    )
    document = KnowledgeIngestionService().upsert_document(
        source=source,
        external_id="semantic-doc",
        title="Manual de reservas",
        content="Las reservas premium se coordinan con hospitalidad.",
    )
    chunk = document.chunks.first()
    assert chunk is not None

    retriever = KnowledgeRetriever()
    monkeypatch.setattr(retriever.embedding_service, "embed_query", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda **kwargs: [
            VectorSearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                section=chunk.section,
                content=chunk.content,
                score=0.91,
            )
        ],
    )

    results = retriever.search("hospitality premium visits", channel="public")

    assert results
    assert results[0].chunk_id == chunk.id
