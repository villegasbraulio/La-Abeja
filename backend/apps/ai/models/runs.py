"""Execution and audit models for AI runs."""

from __future__ import annotations

import uuid

from django.db import models

from .conversations import Conversation


class AgentRun(models.Model):
    """Audit record for a single agent turn."""

    class AgentType(models.TextChoices):
        SUPPORT = "support", "Support"
        OPS = "ops", "Operations"
        WORKFLOW = "workflow", "Workflow"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        related_name="runs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    agent_type = models.CharField(max_length=30, choices=AgentType.choices)
    model = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    intent = models.CharField(max_length=50, blank=True)
    message_text = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    citations = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    needs_human = models.BooleanField(default=False)
    prompt_version = models.CharField(max_length=50, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable run identifier."""
        return f"{self.agent_type}:{self.id}"


class ToolExecution(models.Model):
    """Track each tool call performed during a run."""

    class RiskLevel(models.TextChoices):
        READ_ONLY = "read_only", "Read only"
        LOW_RISK_WRITE = "low_risk_write", "Low risk write"
        HIGH_RISK_WRITE = "high_risk_write", "High risk write"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(AgentRun, related_name="tool_executions", on_delete=models.CASCADE)
    tool_name = models.CharField(max_length=100)
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.READ_ONLY,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        """Return a readable tool execution label."""
        return f"{self.run_id}:{self.tool_name}"
