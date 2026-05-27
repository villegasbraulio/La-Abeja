"""Serializers for the AI API."""

from __future__ import annotations

from rest_framework import serializers

from apps.ai.models import (
    AgentRun,
    ApprovalRequest,
    Conversation,
    ConversationFeedback,
    ConversationTurn,
    KnowledgeDocument,
    KnowledgeSource,
    ToolExecution,
    WorkflowRun,
)


class ConversationTurnSerializer(serializers.ModelSerializer):
    """Serialize conversation turns."""

    class Meta:
        model = ConversationTurn
        fields = ["id", "role", "content", "citations", "metadata", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    """Serialize conversation sessions."""

    turns = ConversationTurnSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "mode",
            "status",
            "last_intent",
            "summary",
            "metadata",
            "created_at",
            "updated_at",
            "turns",
        ]


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Create a chat session."""

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "mode",
            "session_key",
            "metadata",
            "status",
            "last_intent",
            "summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "last_intent",
            "summary",
            "created_at",
            "updated_at",
        ]


class ConversationMessageSerializer(serializers.Serializer):
    """Input serializer for a new message."""

    message = serializers.CharField(max_length=5000)


class ConversationFeedbackSerializer(serializers.ModelSerializer):
    """Serialize feedback submissions."""

    class Meta:
        model = ConversationFeedback
        fields = ["turn", "value", "note"]


class ToolExecutionSerializer(serializers.ModelSerializer):
    """Serialize tool executions."""

    class Meta:
        model = ToolExecution
        fields = [
            "id",
            "tool_name",
            "risk_level",
            "status",
            "input_payload",
            "output_payload",
            "latency_ms",
            "error",
            "created_at",
        ]


class AgentRunSerializer(serializers.ModelSerializer):
    """Serialize agent run details."""

    tool_executions = ToolExecutionSerializer(many=True, read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "agent_type",
            "model",
            "status",
            "intent",
            "message_text",
            "response_text",
            "citations",
            "metadata",
            "confidence",
            "needs_human",
            "prompt_version",
            "created_at",
            "updated_at",
            "tool_executions",
        ]


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    """Serialize knowledge sources."""

    class Meta:
        model = KnowledgeSource
        fields = [
            "id",
            "name",
            "source_type",
            "uri",
            "is_active",
            "sync_cursor",
            "last_synced_at",
            "metadata",
            "created_at",
            "updated_at",
        ]


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Serialize knowledge documents."""

    source_name = serializers.CharField(source="source.name", read_only=True)
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "source",
            "source_name",
            "external_id",
            "title",
            "language",
            "channel",
            "checksum",
            "metadata",
            "is_active",
            "published_at",
            "chunk_count",
            "created_at",
            "updated_at",
        ]

    def get_chunk_count(self, obj: KnowledgeDocument) -> int:
        """Return the number of chunks for a document."""
        return obj.chunks.count()


class CopilotMessageSerializer(serializers.Serializer):
    """Input serializer for backoffice copilot messages."""

    conversation_id = serializers.UUIDField(required=False)
    message = serializers.CharField(max_length=5000)


class WorkflowRunSerializer(serializers.ModelSerializer):
    """Serialize workflow runs."""

    class Meta:
        model = WorkflowRun
        fields = [
            "id",
            "workflow_type",
            "status",
            "actor_type",
            "input_payload",
            "result_payload",
            "idempotency_key",
            "created_at",
            "updated_at",
        ]


class ApprovalRequestSerializer(serializers.ModelSerializer):
    """Serialize approval requests."""

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "workflow_run",
            "action_name",
            "action_payload",
            "status",
            "approved_by",
            "decision_note",
            "decided_at",
            "created_at",
        ]


class ApprovalDecisionSerializer(serializers.Serializer):
    """Approve or reject a risky action."""

    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
