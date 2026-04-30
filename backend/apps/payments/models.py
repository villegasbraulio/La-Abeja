"""Payment models."""

from __future__ import annotations

import uuid

from django.db import models


class Payment(models.Model):
    """MercadoPago-backed payment record."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"
        IN_PROCESS = "in_process", "En proceso"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    mp_preference_id = models.CharField(max_length=100)
    mp_payment_id = models.CharField(max_length=100, blank=True)
    mp_merchant_order_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    status_detail = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_type = models.CharField(max_length=50, blank=True)
    installments = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="ARS")
    invoice_pdf_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Return a readable payment label."""
        return f"{self.order.order_number} - {self.status}"


class PaymentWebhookLog(models.Model):
    """Persist raw payment webhooks for audit and replay."""

    mp_notification_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return a concise webhook identifier."""
        return f"{self.topic} - {self.mp_notification_id}"
