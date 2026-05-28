"""Knowledge retrieval tools."""

from __future__ import annotations

from apps.ai.rag.retriever import KnowledgeRetriever

from .base import ToolContext


def search_knowledge_base(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search public or internal AI knowledge."""
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"results": []}
    channel = "internal" if context.is_staff else "public"
    results = KnowledgeRetriever().search(query, channel=channel)
    return {
        "results": [
            {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.document_title,
                "section": result.section,
                "content": result.content,
                "score": result.score,
            }
            for result in results
        ]
    }


def search_policies(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search policy-style docs such as shipping, payment, and returns guidance."""
    return _filtered_search(
        payload=payload,
        channel="public",
        title_keywords=("guia", "politica", "envios", "retiro", "pagos", "devoluciones", "cambios"),
    )


def search_playbooks(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search internal playbooks, SOPs, and escalation instructions."""
    return _filtered_search(
        payload=payload,
        channel="internal" if context.is_staff else "public",
        title_keywords=("playbook", "interno", "procedimiento", "escalar", "sop", "operaciones"),
    )


def get_answerable_sources(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return the source documents that best support an answer for a query."""
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"sources": []}

    limit = max(1, min(int(payload.get("limit") or 5), 10))
    retriever = KnowledgeRetriever()
    results = retriever.search(query, channel="public", limit=max(limit * 2, 6))
    if context.is_staff:
        internal_results = retriever.search(query, channel="internal", limit=max(limit * 2, 6))
        seen_chunk_ids = {result.chunk_id for result in results}
        results.extend([result for result in internal_results if result.chunk_id not in seen_chunk_ids])
    unique_sources: dict[int, dict[str, object]] = {}
    for result in results:
        unique_sources.setdefault(
            result.document_id,
            {
                "document_id": result.document_id,
                "document_title": result.document_title,
                "sections": [],
                "top_score": result.score,
            },
        )
        if result.section and result.section not in unique_sources[result.document_id]["sections"]:
            unique_sources[result.document_id]["sections"].append(result.section)

    return {
        "sources": list(unique_sources.values())[:limit],
    }


def _filtered_search(
    *,
    payload: dict[str, object],
    channel: str,
    title_keywords: tuple[str, ...],
) -> dict[str, object]:
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"results": []}

    results = KnowledgeRetriever().search(query, channel=channel, limit=12)
    filtered = []
    for result in results:
        title_lower = result.document_title.lower()
        if any(keyword in title_lower for keyword in title_keywords):
            filtered.append(result)
            continue
        if any(keyword in result.content.lower() for keyword in title_keywords):
            filtered.append(result)
            continue
        if "playbook" in title_keywords and "intern" in title_lower:
            filtered.append(result)

    filtered = filtered or results
    return {
        "results": [
            {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.document_title,
                "section": result.section,
                "content": result.content,
                "score": result.score,
            }
            for result in filtered[: max(1, min(int(payload.get("limit") or 5), 10))]
        ]
    }
