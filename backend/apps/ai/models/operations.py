"""Operational models created by the AI layer."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.catalog.models import Wine
from apps.orders.models import Order

from .conversations import Conversation
from .workflows import WorkflowRun


class SupportTask(models.Model):
    """Track internal tasks generated from support or ops flows."""

    class TaskType(models.TextChoices):
        SUPPORT_FOLLOW_UP = "support_follow_up", "Support follow-up"
        ORDER_ISSUE = "order_issue", "Order issue"
        ORDER_REVIEW = "order_review", "Order review"
        PAYMENT_REVIEW = "payment_review", "Payment review"
        LEAD_FOLLOW_UP = "lead_follow_up", "Lead follow-up"
        CONVERSATION_ESCALATION = "conversation_escalation", "Conversation escalation"
        RESTOCK = "restock", "Restock"
        SHIPPING_CLAIM = "shipping_claim", "Shipping claim"
        CANCELLATION_REVIEW = "cancellation_review", "Cancellation review"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=50, choices=TaskType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    order = models.ForeignKey(
        Order,
        related_name="ai_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    conversation = models.ForeignKey(
        Conversation,
        related_name="support_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ai_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_ai_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_ai_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    workflow_run = models.ForeignKey(
        WorkflowRun,
        related_name="support_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    due_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable task label."""
        return f"{self.task_type}:{self.title}"


class InternalNote(models.Model):
    """Structured internal notes linked to business entities."""

    class NoteType(models.TextChoices):
        GENERAL = "general", "General"
        ORDER = "order", "Order"
        CUSTOMER = "customer", "Customer"
        SUPPORT = "support", "Support"
        SALES = "sales", "Sales"
        PAYMENT = "payment", "Payment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note_type = models.CharField(max_length=30, choices=NoteType.choices, default=NoteType.GENERAL)
    content = models.TextField()
    order = models.ForeignKey(
        Order,
        related_name="ai_notes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    conversation = models.ForeignKey(
        Conversation,
        related_name="internal_notes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ai_notes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_ai_notes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable note label."""
        return f"{self.note_type}:{self.id}"


class Lead(models.Model):
    """Commercial lead captured by the AI layer."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        QUALIFIED = "qualified", "Qualified"
        CONTACTED = "contacted", "Contacted"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    source_channel = models.CharField(max_length=30, default=Conversation.Channel.WEB)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    interest_summary = models.TextField(blank=True)
    desired_varietals = models.JSONField(default=list, blank=True)
    estimated_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conversation = models.ForeignKey(
        Conversation,
        related_name="leads",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="leads",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_leads",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable lead label."""
        return self.full_name


class StockReservation(models.Model):
    """Persist stock reservations executed or approved through the AI layer."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PARTIALLY_RELEASED = "partially_released", "Partially released"
        RELEASED = "released", "Released"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wine = models.ForeignKey(
        Wine,
        related_name="ai_stock_reservations",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField()
    order = models.ForeignKey(
        Order,
        related_name="ai_stock_reservations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    conversation = models.ForeignKey(
        Conversation,
        related_name="stock_reservations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ai_stock_reservations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_stock_reservations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    workflow_run = models.ForeignKey(
        WorkflowRun,
        related_name="stock_reservations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE)
    reason = models.TextField(blank=True)
    released_quantity = models.PositiveIntegerField(default=0)
    released_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable reservation label."""
        return f"{self.wine.sku}:{self.quantity}:{self.status}"
