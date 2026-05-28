"""Serializers for the AI API."""

from __future__ import annotations

from rest_framework import serializers

from apps.ai.models import (
    AgentRun,
    ApprovalRequest,
    Conversation,
    ConversationFeedback,
    ConversationTurn,
    Lead,
    KnowledgeDocument,
    KnowledgeSource,
    SupportTask,
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

    workflow_type = serializers.CharField(source="workflow_run.workflow_type", read_only=True, allow_null=True)
    workflow_status = serializers.CharField(source="workflow_run.status", read_only=True, allow_null=True)
    workflow_result = serializers.JSONField(source="workflow_run.result_payload", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True, allow_null=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "workflow_run",
            "workflow_type",
            "workflow_status",
            "workflow_result",
            "action_name",
            "action_payload",
            "status",
            "approved_by",
            "approved_by_email",
            "decision_note",
            "decided_at",
            "created_at",
        ]


class ApprovalDecisionSerializer(serializers.Serializer):
    """Approve or reject a risky action."""

    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class SupportTaskSerializer(serializers.ModelSerializer):
    """Serialize AI-created support and operations tasks."""

    order_number = serializers.CharField(source="order.order_number", read_only=True, allow_null=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True, allow_null=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True, allow_null=True)
    assigned_to_email = serializers.EmailField(source="assigned_to.email", read_only=True, allow_null=True)
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, allow_null=True)
    workflow_type = serializers.CharField(source="workflow_run.workflow_type", read_only=True, allow_null=True)

    class Meta:
        model = SupportTask
        fields = [
            "id",
            "task_type",
            "title",
            "description",
            "status",
            "priority",
            "order",
            "order_number",
            "conversation",
            "customer_email",
            "customer_name",
            "assigned_to_email",
            "assigned_to_name",
            "workflow_run",
            "workflow_type",
            "due_at",
            "metadata",
            "created_at",
            "updated_at",
        ]


class SupportTaskUpdateSerializer(serializers.ModelSerializer):
    """Update lightweight operational task fields."""

    assigned_to_email = serializers.EmailField(required=False)

    class Meta:
        model = SupportTask
        fields = ["status", "priority", "assigned_to_email", "due_at"]

    def validate_assigned_to_email(self, value: str) -> str:
        """Require assignments to point to a staff user."""
        if not value:
            return value
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        if not user_model.objects.filter(email__iexact=value, is_staff=True).exists():
            raise serializers.ValidationError("No encontramos un usuario staff con ese email.")
        return value.lower()

    def update(self, instance: SupportTask, validated_data: dict[str, object]) -> SupportTask:
        """Resolve assignee email into a user relation before persisting."""
        assigned_to_email = validated_data.pop("assigned_to_email", None)
        if assigned_to_email is not None:
            from django.contrib.auth import get_user_model

            user_model = get_user_model()
            instance.assigned_to = user_model.objects.filter(
                email__iexact=str(assigned_to_email),
                is_staff=True,
            ).first()
        return super().update(instance, validated_data)


class LeadSerializer(serializers.ModelSerializer):
    """Serialize AI-captured leads."""

    customer_email = serializers.EmailField(source="customer.email", read_only=True, allow_null=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True, allow_null=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "company",
            "source_channel",
            "status",
            "interest_summary",
            "desired_varietals",
            "estimated_order_value",
            "conversation",
            "customer_email",
            "customer_name",
            "metadata",
            "created_at",
            "updated_at",
        ]


class LeadUpdateSerializer(serializers.ModelSerializer):
    """Update lightweight lead fields from the backoffice."""

    class Meta:
        model = Lead
        fields = ["status", "interest_summary", "estimated_order_value"]
