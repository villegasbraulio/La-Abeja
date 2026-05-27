"""Memory models for lightweight structured conversational state."""

from __future__ import annotations

from django.db import models

from .conversations import Conversation


class MemoryFact(models.Model):
    """Structured memory fact extracted from the conversation."""

    conversation = models.ForeignKey(
        Conversation,
        related_name="facts",
        on_delete=models.CASCADE,
    )
    fact_type = models.CharField(max_length=50)
    key = models.CharField(max_length=100)
    value = models.JSONField(default=dict, blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=0.800)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "fact_type", "key"],
                name="unique_memory_fact_per_conversation",
            )
        ]

    def __str__(self) -> str:
        """Return a readable memory fact label."""
        return f"{self.conversation_id}:{self.fact_type}:{self.key}"
