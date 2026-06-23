"""Durable automation and transactional outbox models."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class OutboxEvent(models.Model):
    """A durable external side effect committed with business data."""

    class EventType(models.TextChoices):
        ORDER_EMAIL = "order.email", "Email de pedido"
        ANDREANI_FULFILLMENT = "order.andreani", "Despacho Andreani"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PROCESSING = "processing", "Procesando"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_key = models.CharField(max_length=180, unique=True)
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["status", "available_at"])]

    def __str__(self) -> str:
        """Return the event type and durable key."""
        return f"{self.event_type}: {self.event_key}"
