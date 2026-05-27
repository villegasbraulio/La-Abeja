"""Admin registrations for AI models."""

from __future__ import annotations

from django.contrib import admin

from .models import (
    AgentRun,
    ApprovalRequest,
    Conversation,
    ConversationFeedback,
    ConversationTurn,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    MemoryFact,
    ToolExecution,
    WorkflowRun,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin configuration for conversations."""

    list_display = ("id", "mode", "channel", "status", "customer", "last_intent", "updated_at")
    list_filter = ("mode", "channel", "status")
    search_fields = ("id", "customer__email", "summary", "last_intent")


@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    """Admin configuration for turns."""

    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("conversation__id", "content")


@admin.register(ConversationFeedback)
class ConversationFeedbackAdmin(admin.ModelAdmin):
    """Admin configuration for feedback."""

    list_display = ("id", "conversation", "value", "created_at")
    list_filter = ("value",)


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    """Admin configuration for knowledge sources."""

    list_display = ("name", "source_type", "is_active", "last_synced_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "uri")


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for knowledge documents."""

    list_display = ("title", "source", "channel", "language", "is_active", "updated_at")
    list_filter = ("channel", "language", "is_active")
    search_fields = ("title", "external_id")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    """Admin configuration for chunks."""

    list_display = ("document", "chunk_index", "section", "updated_at")
    search_fields = ("document__title", "section", "content")


@admin.register(MemoryFact)
class MemoryFactAdmin(admin.ModelAdmin):
    """Admin configuration for memory facts."""

    list_display = ("conversation", "fact_type", "key", "confidence", "updated_at")
    list_filter = ("fact_type",)
    search_fields = ("conversation__id", "key")


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    """Admin configuration for agent runs."""

    list_display = ("id", "agent_type", "status", "intent", "needs_human", "created_at")
    list_filter = ("agent_type", "status", "needs_human")
    search_fields = ("id", "intent", "message_text", "response_text")


@admin.register(ToolExecution)
class ToolExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for tool executions."""

    list_display = ("run", "tool_name", "status", "risk_level", "latency_ms", "created_at")
    list_filter = ("status", "risk_level")
    search_fields = ("run__id", "tool_name")


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    """Admin configuration for workflow runs."""

    list_display = ("id", "workflow_type", "status", "actor_type", "created_at")
    list_filter = ("status", "actor_type", "workflow_type")
    search_fields = ("id", "workflow_type", "idempotency_key")


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    """Admin configuration for approvals."""

    list_display = ("workflow_run", "action_name", "status", "approved_by", "created_at")
    list_filter = ("status",)
    search_fields = ("workflow_run__id", "action_name")
