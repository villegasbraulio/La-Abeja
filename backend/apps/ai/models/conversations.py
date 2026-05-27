"""Conversation models for the AI app."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Top-level container for chat interactions."""

    class Channel(models.TextChoices):
        WEB = "web", "Web"
        BACKOFFICE = "backoffice", "Backoffice"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"

    class Mode(models.TextChoices):
        SUPPORT = "support", "Support"
        OPS = "ops", "Operations"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ESCALATED = "escalated", "Escalated"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=30, choices=Channel.choices, default=Channel.WEB)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.SUPPORT)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_conversations",
    )
    session_key = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    last_intent = models.CharField(max_length=50, blank=True)
    summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        """Return a concise conversation identifier."""
        return f"{self.mode}:{self.channel}:{self.id}"


class ConversationTurn(models.Model):
    """A single message or system/tool event inside a conversation."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        related_name="turns",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    citations = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        """Return a readable turn label."""
        return f"{self.conversation_id}:{self.role}"


class ConversationFeedback(models.Model):
    """Store thumbs-up or thumbs-down style feedback on assistant replies."""

    class Value(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        related_name="feedback_items",
        on_delete=models.CASCADE,
    )
    turn = models.ForeignKey(
        ConversationTurn,
        related_name="feedback_items",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    value = models.CharField(max_length=20, choices=Value.choices)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable feedback label."""
        return f"{self.conversation_id}:{self.value}"
