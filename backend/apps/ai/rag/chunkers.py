"""Chunking utilities for knowledge ingestion."""

from __future__ import annotations

from hashlib import sha256


def chunk_text(title: str, content: str, max_chars: int = 650) -> list[dict[str, object]]:
    """Split content into retrieval-friendly chunks using paragraph boundaries first."""
    paragraphs = [paragraph.strip() for paragraph in content.split("\n") if paragraph.strip()]
    chunks: list[dict[str, object]] = []
    buffer: list[str] = []
    section = title
    current_length = 0

    for paragraph in paragraphs:
        if current_length and current_length + len(paragraph) > max_chars:
            text = "\n".join(buffer).strip()
            chunks.append(
                {
                    "section": section,
                    "content": text,
                    "token_count": max(len(text.split()), 1),
                    "content_hash": sha256(text.encode("utf-8")).hexdigest(),
                }
            )
            buffer = [paragraph]
            current_length = len(paragraph)
            continue

        buffer.append(paragraph)
        current_length += len(paragraph)

    if buffer:
        text = "\n".join(buffer).strip()
        chunks.append(
            {
                "section": section,
                "content": text,
                "token_count": max(len(text.split()), 1),
                "content_hash": sha256(text.encode("utf-8")).hexdigest(),
            }
        )

    return chunks
