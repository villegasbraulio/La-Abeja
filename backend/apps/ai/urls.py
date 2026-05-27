"""URL routes for the AI app."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AIApprovalApproveView,
    AIApprovalRejectView,
    AIChatSessionCreateView,
    AIChatSessionDetailView,
    AIChatSessionEventsView,
    AIChatSessionFeedbackView,
    AIChatSessionMessageView,
    AICopilotMessageView,
    AIKnowledgeDocumentListView,
    AIKnowledgeReindexView,
    AIKnowledgeSourceListCreateView,
    AIKnowledgeSourceSyncView,
    AIMetricsSummaryView,
    AIRunDetailView,
    AIRunStepsView,
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
    path("runs/<uuid:pk>/", AIRunDetailView.as_view(), name="run-detail"),
    path("runs/<uuid:pk>/steps/", AIRunStepsView.as_view(), name="run-steps"),
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
