"""Views for the AI app."""

# ruff: noqa: E501

from __future__ import annotations

from uuid import uuid4

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.agents.orchestrator import AIOrchestrator
from apps.ai.models import (
    AgentRun,
    ApprovalRequest,
    Conversation,
    ConversationFeedback,
    KnowledgeDocument,
    KnowledgeSource,
    Lead,
    StockReservation,
    SupportTask,
    ToolExecution,
    WorkflowRun,
)
from apps.ai.services.approval_service import ApprovalService
from apps.ai.tasks.ingestion_tasks import sync_knowledge_source
from apps.authentication.permissions import IsStaffUser

from .permissions import IsStaffOrReadOnlyConversation
from .serializers import (
    AgentRunSerializer,
    ApprovalDecisionSerializer,
    ApprovalRequestSerializer,
    ConversationCreateSerializer,
    ConversationFeedbackSerializer,
    ConversationMessageSerializer,
    ConversationSerializer,
    CopilotMessageSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeSourceSerializer,
    LeadSerializer,
    LeadUpdateSerializer,
    StockReservationSerializer,
    SupportTaskSerializer,
    SupportTaskUpdateSerializer,
    ToolExecutionSerializer,
    WorkflowRunSerializer,
)


class AIChatSessionCreateView(generics.CreateAPIView):
    """Create a customer or staff-facing AI conversation."""

    serializer_class = ConversationCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer: ConversationCreateSerializer) -> None:
        """Associate authenticated users with the conversation automatically."""
        customer = self.request.user if self.request.user.is_authenticated else None
        serializer.save(customer=customer)


class AIChatSessionDetailView(generics.RetrieveAPIView):
    """Return a full chat session with turns."""

    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnlyConversation]
    queryset = Conversation.objects.prefetch_related("turns")


class AIChatSessionMessageView(APIView):
    """Append a message to a chat session and run the orchestrator."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, pk: str) -> Response:
        """Generate an assistant response for the provided session."""
        conversation = get_object_or_404(Conversation, pk=pk)
        if request.user.is_authenticated:
            if request.user.is_staff:
                pass
            elif conversation.customer_id and conversation.customer_id != request.user.id:
                return Response(status=status.HTTP_403_FORBIDDEN)
        elif conversation.customer_id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ConversationMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AIOrchestrator().handle_message(
            conversation=conversation,
            message=serializer.validated_data["message"],
            user_id=str(request.user.id) if request.user.is_authenticated else None,
            is_staff=bool(request.user.is_authenticated and request.user.is_staff),
        )
        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "assistant_turn": {
                    "id": str(result.assistant_turn.id),
                    "content": result.assistant_turn.content,
                    "citations": result.assistant_turn.citations,
                    "metadata": result.assistant_turn.metadata,
                    "created_at": result.assistant_turn.created_at,
                },
                "run": AgentRunSerializer(result.run).data,
            }
        )


class AIChatSessionEventsView(generics.RetrieveAPIView):
    """Return the latest turns in a session."""

    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnlyConversation]
    queryset = Conversation.objects.prefetch_related("turns")


class AIChatSessionFeedbackView(APIView):
    """Persist user feedback for a conversation."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, pk: str) -> Response:
        """Store simple positive or negative feedback."""
        conversation = get_object_or_404(Conversation, pk=pk)
        serializer = ConversationFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ConversationFeedback.objects.create(conversation=conversation, **serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED)


class AICopilotMessageView(APIView):
    """Staff-only entrypoint for the operations copilot."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request: Request) -> Response:
        """Create or reuse a backoffice conversation and run the orchestrator."""
        serializer = CopilotMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(
                Conversation.objects.prefetch_related("turns"),
                pk=conversation_id,
                mode=Conversation.Mode.OPS,
            )
        else:
            conversation = Conversation.objects.create(
                channel=Conversation.Channel.BACKOFFICE,
                mode=Conversation.Mode.OPS,
                customer=request.user,
            )
        result = AIOrchestrator().handle_message(
            conversation=conversation,
            message=serializer.validated_data["message"],
            user_id=str(request.user.id),
            is_staff=True,
        )
        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "assistant_turn": {
                    "id": str(result.assistant_turn.id),
                    "content": result.assistant_turn.content,
                    "citations": result.assistant_turn.citations,
                    "metadata": result.assistant_turn.metadata,
                    "created_at": result.assistant_turn.created_at,
                },
                "run": AgentRunSerializer(result.run).data,
            }
        )


class AICopilotOverviewView(APIView):
    """Return the current AI operations overview for the backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Return prompt suggestions, queue counts, and recent artifacts."""
        del request
        payload = {
            "metrics": {
                "open_tasks": SupportTask.objects.filter(
                    status__in=[
                        SupportTask.Status.OPEN,
                        SupportTask.Status.IN_PROGRESS,
                        SupportTask.Status.BLOCKED,
                    ]
                ).count(),
                "new_leads": Lead.objects.filter(status=Lead.Status.NEW).count(),
                "pending_approvals": ApprovalRequest.objects.filter(
                    status=ApprovalRequest.Status.PENDING
                ).count(),
                "runs_needing_human": AgentRun.objects.filter(needs_human=True).count(),
                "active_stock_reservations": StockReservation.objects.filter(
                    status__in=[
                        StockReservation.Status.ACTIVE,
                        StockReservation.Status.PARTIALLY_RELEASED,
                    ]
                ).count(),
                "pending_cancellation_approvals": ApprovalRequest.objects.filter(
                    status=ApprovalRequest.Status.PENDING,
                    action_name="request_order_cancellation",
                ).count(),
            },
            "prompt_suggestions": [
                "Mostrame el stock bajo",
                "Decime las ventas de los últimos 30 días",
                "Qué varietales venden más este mes?",
                "Buscá pedidos con pago rechazado de los últimos 7 días",
                "Traeme el 360 del cliente ana@example.com",
                "Creá un seguimiento de pago para LAB-2026-000145",
                "Abrí un reclamo logístico para LAB-2026-000145 porque no hay movimiento del tracking",
                "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
                "Pedí cancelación del pedido LAB-2026-000145 por solicitud del cliente",
            ],
            "recent_tasks": SupportTaskSerializer(
                SupportTask.objects.select_related(
                    "order", "customer", "assigned_to", "workflow_run"
                )[:5],
                many=True,
            ).data,
            "recent_leads": LeadSerializer(
                Lead.objects.select_related("customer", "conversation")[:5],
                many=True,
            ).data,
            "recent_stock_reservations": StockReservationSerializer(
                StockReservation.objects.select_related(
                    "wine", "order", "customer", "workflow_run"
                )[:5],
                many=True,
            ).data,
            "pending_approvals": ApprovalRequestSerializer(
                ApprovalRequest.objects.select_related("workflow_run", "approved_by").filter(
                    status=ApprovalRequest.Status.PENDING
                )[:5],
                many=True,
            ).data,
            "pending_cancellation_approvals": ApprovalRequestSerializer(
                ApprovalRequest.objects.select_related("workflow_run", "approved_by").filter(
                    status=ApprovalRequest.Status.PENDING,
                    action_name="request_order_cancellation",
                )[:5],
                many=True,
            ).data,
        }
        return Response(payload)


class AIRunDetailView(generics.RetrieveAPIView):
    """Expose audit details for a single run."""

    serializer_class = AgentRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = AgentRun.objects.prefetch_related("tool_executions")


class AIRunStepsView(generics.ListAPIView):
    """Return tool execution steps for a run."""

    serializer_class = ToolExecutionSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get_queryset(self):  # type: ignore[override]
        """Filter tool executions by run ID."""
        run = get_object_or_404(AgentRun, pk=self.kwargs["pk"])
        return ToolExecution.objects.filter(run=run)


class AITaskListView(generics.ListAPIView):
    """List AI-generated support tasks for the backoffice."""

    serializer_class = SupportTaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    pagination_class = None

    def get_queryset(self):  # type: ignore[override]
        """Filter tasks by status, task type, search, or conversation."""
        queryset = SupportTask.objects.select_related(
            "order", "customer", "assigned_to", "workflow_run"
        )
        status_filter = self.request.query_params.get("status")
        task_type = self.request.query_params.get("task_type")
        conversation_id = self.request.query_params.get("conversation_id")
        search = (self.request.query_params.get("search") or "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(order__order_number__icontains=search)
                | Q(customer__email__icontains=search)
            )
        return queryset


class AITaskDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update an AI-generated task."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = SupportTask.objects.select_related(
        "order", "customer", "assigned_to", "workflow_run"
    )

    def get_serializer_class(self):  # type: ignore[override]
        """Use a lighter serializer for partial updates."""
        if self.request.method in {"PATCH", "PUT"}:
            return SupportTaskUpdateSerializer
        return SupportTaskSerializer


class AILeadListView(generics.ListAPIView):
    """List AI-captured leads."""

    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    pagination_class = None

    def get_queryset(self):  # type: ignore[override]
        """Filter leads by status, search, or conversation."""
        queryset = Lead.objects.select_related("customer", "conversation")
        status_filter = self.request.query_params.get("status")
        conversation_id = self.request.query_params.get("conversation_id")
        search = (self.request.query_params.get("search") or "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(company__icontains=search)
                | Q(interest_summary__icontains=search)
            )
        return queryset


class AILeadDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update an AI-captured lead."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = Lead.objects.select_related("customer", "conversation")

    def get_serializer_class(self):  # type: ignore[override]
        """Use the lighter serializer for updates."""
        if self.request.method in {"PATCH", "PUT"}:
            return LeadUpdateSerializer
        return LeadSerializer


class AIApprovalListView(generics.ListAPIView):
    """List approval requests for the AI layer."""

    serializer_class = ApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    pagination_class = None

    def get_queryset(self):  # type: ignore[override]
        """Filter approvals by status or action name."""
        queryset = ApprovalRequest.objects.select_related("workflow_run", "approved_by")
        status_filter = self.request.query_params.get("status")
        action_name = self.request.query_params.get("action_name")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if action_name:
            queryset = queryset.filter(action_name=action_name)
        return queryset


class AIStockReservationListView(generics.ListAPIView):
    """List AI-managed stock reservations for the backoffice."""

    serializer_class = StockReservationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    pagination_class = None

    def get_queryset(self):  # type: ignore[override]
        """Filter reservations by status or search terms."""
        queryset = StockReservation.objects.select_related(
            "wine", "order", "customer", "workflow_run"
        )
        status_filter = self.request.query_params.get("status")
        search = (self.request.query_params.get("search") or "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(wine__name__icontains=search)
                | Q(wine__sku__icontains=search)
                | Q(order__order_number__icontains=search)
                | Q(customer__email__icontains=search)
                | Q(reason__icontains=search)
            )
        return queryset


class AIApprovalDetailView(generics.RetrieveAPIView):
    """Retrieve a single approval request with workflow context."""

    serializer_class = ApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = ApprovalRequest.objects.select_related("workflow_run", "approved_by")


class AIApprovalApproveView(APIView):
    """Approve a pending AI action."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request: Request, pk: str) -> Response:
        """Approve and execute a pending AI action."""
        approval = get_object_or_404(ApprovalRequest, pk=pk)
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = ApprovalService().approve(
            approval=approval,
            approved_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(ApprovalRequestSerializer(approval).data)


class AIApprovalRejectView(APIView):
    """Reject a pending AI action."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request: Request, pk: str) -> Response:
        """Reject a pending AI action and cancel its workflow."""
        approval = get_object_or_404(ApprovalRequest, pk=pk)
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = ApprovalService().reject(
            approval=approval,
            approved_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(ApprovalRequestSerializer(approval).data)


class AIKnowledgeSourceListCreateView(generics.ListCreateAPIView):
    """Create and list knowledge sources."""

    serializer_class = KnowledgeSourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = KnowledgeSource.objects.all()


class AIKnowledgeSourceSyncView(APIView):
    """Queue a knowledge source sync."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request: Request, pk: int) -> Response:
        """Dispatch a sync task for the given source."""
        source = get_object_or_404(KnowledgeSource, pk=pk)
        task_result = sync_knowledge_source.delay(source.id)
        return Response({"task_id": task_result.id, "source_id": source.id})


class AIKnowledgeDocumentListView(generics.ListAPIView):
    """List known documents."""

    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = KnowledgeDocument.objects.select_related("source").prefetch_related("chunks")


class AIKnowledgeReindexView(APIView):
    """Return a lightweight reindex acknowledgement."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request: Request) -> Response:
        """Acknowledge a reindex request."""
        del request
        return Response({"status": "accepted"})


class _BaseWorkflowRunView(APIView):
    """Shared workflow creation helper."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    workflow_type = ""

    def post(self, request: Request) -> Response:
        """Create a new workflow run."""
        workflow = WorkflowRun.objects.create(
            workflow_type=self.workflow_type,
            status=WorkflowRun.Status.PENDING,
            actor_type="human",
            input_payload=request.data,
            result_payload={},
            idempotency_key=f"{self.workflow_type}-{uuid4()}",
        )
        return Response(WorkflowRunSerializer(workflow).data, status=status.HTTP_201_CREATED)


class AIWorkflowLeadTriageRunView(_BaseWorkflowRunView):
    """Create a lead triage workflow run."""

    workflow_type = "lead_triage"


class AIWorkflowOrderExceptionRunView(_BaseWorkflowRunView):
    """Create an order exception workflow run."""

    workflow_type = "order_exception"


class AIWorkflowAbandonedCartRunView(_BaseWorkflowRunView):
    """Create an abandoned cart workflow run."""

    workflow_type = "abandoned_cart"


class AIWorkflowRunDetailView(generics.RetrieveAPIView):
    """Retrieve a workflow run."""

    serializer_class = WorkflowRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = WorkflowRun.objects.all()


class AIMetricsSummaryView(APIView):
    """Return a compact operations summary for the AI layer."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Aggregate summary KPIs for the AI app."""
        del request
        payload = {
            "conversations": Conversation.objects.count(),
            "open_conversations": Conversation.objects.filter(
                status=Conversation.Status.OPEN
            ).count(),
            "agent_runs": AgentRun.objects.count(),
            "runs_needing_human": AgentRun.objects.filter(needs_human=True).count(),
            "knowledge_documents": KnowledgeDocument.objects.count(),
            "knowledge_sources": KnowledgeSource.objects.count(),
            "workflow_runs": WorkflowRun.objects.count(),
            "tool_executions": ToolExecution.objects.count(),
            "open_tasks": SupportTask.objects.filter(
                status__in=[
                    SupportTask.Status.OPEN,
                    SupportTask.Status.IN_PROGRESS,
                    SupportTask.Status.BLOCKED,
                ]
            ).count(),
            "new_leads": Lead.objects.filter(status=Lead.Status.NEW).count(),
            "pending_approvals": ApprovalRequest.objects.filter(
                status=ApprovalRequest.Status.PENDING
            ).count(),
            "top_intents": list(
                AgentRun.objects.exclude(intent="")
                .values("intent")
                .annotate(count=Count("intent"))
                .order_by("-count")[:5]
            ),
        }
        return Response(payload)
