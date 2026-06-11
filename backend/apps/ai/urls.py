"""URL routes for the AI app."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AIApprovalApproveView,
    AIApprovalDetailView,
    AIApprovalListView,
    AIApprovalRejectView,
    AIChatSessionCreateView,
    AIChatSessionDetailView,
    AIChatSessionEventsView,
    AIChatSessionFeedbackView,
    AICopilotOverviewView,
    AIChatSessionMessageView,
    AICopilotMessageView,
    AIKnowledgeDocumentListView,
    AIKnowledgeReindexView,
    AIKnowledgeSourceListCreateView,
    AIKnowledgeSourceSyncView,
    AILeadDetailView,
    AILeadListView,
    AIMetricsSummaryView,
    AIRunDetailView,
    AIRunStepsView,
    AIStockReservationListView,
    AITaskDetailView,
    AITaskListView,
    AIWorkflowAbandonedCartRunView,
    AIWorkflowLeadTriageRunView,
    AIWorkflowOrderExceptionRunView,
    AIWorkflowRunDetailView,
)

app_name = "ai"

urlpatterns = [
    path("chat/sessions/", AIChatSessionCreateView.as_view(), name="chat-session-create"),
    path("chat/sessions/<uuid:pk>/", AIChatSessionDetailView.as_view(), name="chat-session-detail"),
    path(
        "chat/sessions/<uuid:pk>/messages/",
        AIChatSessionMessageView.as_view(),
        name="chat-session-message",
    ),
    path(
        "chat/sessions/<uuid:pk>/events/",
        AIChatSessionEventsView.as_view(),
        name="chat-session-events",
    ),
    path(
        "chat/sessions/<uuid:pk>/feedback/",
        AIChatSessionFeedbackView.as_view(),
        name="chat-session-feedback",
    ),
    path("copilot/messages/", AICopilotMessageView.as_view(), name="copilot-message"),
    path("copilot/overview/", AICopilotOverviewView.as_view(), name="copilot-overview"),
    path("runs/<uuid:pk>/", AIRunDetailView.as_view(), name="run-detail"),
    path("runs/<uuid:pk>/steps/", AIRunStepsView.as_view(), name="run-steps"),
    path("tasks/", AITaskListView.as_view(), name="task-list"),
    path("tasks/<uuid:pk>/", AITaskDetailView.as_view(), name="task-detail"),
    path("stock-reservations/", AIStockReservationListView.as_view(), name="stock-reservation-list"),
    path("leads/", AILeadListView.as_view(), name="lead-list"),
    path("leads/<uuid:pk>/", AILeadDetailView.as_view(), name="lead-detail"),
    path("approvals/", AIApprovalListView.as_view(), name="approval-list"),
    path("approvals/<uuid:pk>/", AIApprovalDetailView.as_view(), name="approval-detail"),
    path("approvals/<uuid:pk>/approve/", AIApprovalApproveView.as_view(), name="approval-approve"),
    path("approvals/<uuid:pk>/reject/", AIApprovalRejectView.as_view(), name="approval-reject"),
    path(
        "knowledge/sources/",
        AIKnowledgeSourceListCreateView.as_view(),
        name="knowledge-source-list",
    ),
    path(
        "knowledge/sources/<int:pk>/sync/",
        AIKnowledgeSourceSyncView.as_view(),
        name="knowledge-source-sync",
    ),
    path("knowledge/documents/", AIKnowledgeDocumentListView.as_view(), name="knowledge-document-list"),
    path("knowledge/reindex/", AIKnowledgeReindexView.as_view(), name="knowledge-reindex"),
    path(
        "workflows/lead-triage/run/",
        AIWorkflowLeadTriageRunView.as_view(),
        name="workflow-lead-triage",
    ),
    path(
        "workflows/order-exception/run/",
        AIWorkflowOrderExceptionRunView.as_view(),
        name="workflow-order-exception",
    ),
    path(
        "workflows/abandoned-cart/run/",
        AIWorkflowAbandonedCartRunView.as_view(),
        name="workflow-abandoned-cart",
    ),
    path("workflows/runs/<uuid:pk>/", AIWorkflowRunDetailView.as_view(), name="workflow-run-detail"),
    path("metrics/summary/", AIMetricsSummaryView.as_view(), name="metrics-summary"),
]
