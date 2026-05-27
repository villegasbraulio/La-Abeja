"""Knowledge base models for AI retrieval."""

from __future__ import annotations

from django.db import models


class KnowledgeSource(models.Model):
    """Represents a logical source of knowledge documents."""

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        FAQ = "faq", "FAQ"
        CMS = "cms", "CMS"
        DOC = "doc", "Document"
        PDF = "pdf", "PDF"

    name = models.CharField(max_length=200)
    source_type = models.CharField(
        max_length=50,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )
    uri = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sync_cursor = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        """Return the source name."""
        return self.name


class KnowledgeDocument(models.Model):
    """A document stored in the knowledge base."""

    class Channel(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"

    source = models.ForeignKey(KnowledgeSource, related_name="documents", on_delete=models.PROTECT)
    external_id = models.CharField(max_length=200)
    title = models.CharField(max_length=300)
    language = models.CharField(max_length=10, default="es-AR")
    channel = models.CharField(max_length=30, choices=Channel.choices, default=Channel.PUBLIC)
    checksum = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="unique_knowledge_document_per_source",
            )
        ]

    def __str__(self) -> str:
        """Return the document title."""
        return self.title


class KnowledgeChunk(models.Model):
    """A retrievable chunk of a knowledge document."""

    document = models.ForeignKey(
        KnowledgeDocument,
        related_name="chunks",
        on_delete=models.CASCADE,
    )
    chunk_index = models.PositiveIntegerField()
    section = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    embedding = models.JSONField(default=list, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    embedding_model = models.CharField(max_length=100, blank=True)
    content_hash = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_chunk_index_per_document",
            )
        ]
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
        ]

    def __str__(self) -> str:
        """Return a concise chunk label."""
        return f"{self.document_id}:{self.chunk_index}"
