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
