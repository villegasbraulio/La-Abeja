"""Add optional pgvector support tables for AI retrieval."""

from __future__ import annotations

from django.conf import settings
from django.db import migrations


def create_pgvector_support(apps, schema_editor) -> None:
    """Create the vector extension and side table only on PostgreSQL."""
    del apps
    if not settings.AI_ENABLE_PGVECTOR or schema_editor.connection.vendor != "postgresql":
        return
    dimensions = min(int(getattr(settings, "AI_EMBEDDING_DIMENSIONS", 1536)), 1536)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute("DROP TABLE IF EXISTS ai_knowledgechunk_embedding;")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS ai_knowledgechunk_embedding (
                chunk_id bigint PRIMARY KEY REFERENCES ai_knowledgechunk(id) ON DELETE CASCADE,
                embedding vector({dimensions}) NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ai_knowledgechunk_embedding_hnsw
            ON ai_knowledgechunk_embedding
            USING hnsw (embedding vector_cosine_ops);
            """
        )


def drop_pgvector_support(apps, schema_editor) -> None:
    """Drop the vector side table on rollback."""
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS ai_knowledgechunk_embedding;")


class Migration(migrations.Migration):
    """Add optional pgvector support."""

    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_pgvector_support, drop_pgvector_support),
    ]
