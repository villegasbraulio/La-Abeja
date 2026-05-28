"""Workflow and approval API tests for the AI app."""

from __future__ import annotations

import pytest
from rest_framework import status

from apps.ai.models import AgentRun, ApprovalRequest, Conversation, InternalNote, ToolExecution, WorkflowRun
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry
from apps.authentication.tests.factories import UserFactory
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory


@pytest.mark.django_db
def test_staff_can_create_lead_triage_workflow(authenticated_client) -> None:
    """Staff users should create workflow runs from the API."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    response = client.post(
        "/api/v1/ai/workflows/lead-triage/run/",
        {"lead_type": "corporate_gift", "message": "Necesito 40 cajas"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["workflow_type"] == "lead_triage"
    assert WorkflowRun.objects.filter(workflow_type="lead_triage").exists()


@pytest.mark.django_db
def test_non_staff_cannot_create_workflow(authenticated_client) -> None:
    """Non-staff users should not hit staff-only workflow endpoints."""
    client, _ = authenticated_client

    response = client.post(
        "/api/v1/ai/workflows/order-exception/run/",
        {"order_number": "LAB-2026-000145"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_staff_can_approve_pending_ai_action(authenticated_client) -> None:
    """Approval endpoint should execute the deferred risky action."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    customer = UserFactory(email="buyer@example.com", phone="+5492604000000")
    order = OrderFactory(user=customer, order_number="LAB-2026-000145", status=Order.Status.PREPARING)
    conversation = Conversation.objects.create(mode=Conversation.Mode.OPS, customer=user)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.OPS)
    result = ToolRegistry().execute(
        tool_name="update_order_status",
        payload={
            "order_number": order.order_number,
            "new_status": "shipped",
            "tracking_number": "AND-145",
            "note": "Despacho aprobado por operaciones.",
        },
        context=ToolContext(run=run, user_id=str(user.id), is_staff=True),
    )
    approval = ApprovalRequest.objects.get(id=result["approval_request_id"])

    response = client.post(
        f"/api/v1/ai/approvals/{approval.id}/approve/",
        {"note": "Proceder"},
        format="json",
    )

    order.refresh_from_db()
    approval.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert approval.status == ApprovalRequest.Status.APPROVED
    assert approval.approved_by_id == user.id
    assert approval.decision_note == "Proceder"
    assert approval.workflow_run.status == WorkflowRun.Status.COMPLETED
    assert order.status == Order.Status.SHIPPED
    assert order.tracking_number == "AND-145"
    assert ToolExecution.objects.filter(run__agent_type=AgentRun.AgentType.WORKFLOW, tool_name="update_order_status").exists()
    assert InternalNote.objects.filter(order=order, note_type="order").exists()


@pytest.mark.django_db
def test_staff_can_reject_pending_ai_action(authenticated_client) -> None:
    """Reject endpoint should cancel the deferred workflow."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    conversation = Conversation.objects.create(mode=Conversation.Mode.OPS, customer=user)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.OPS)
    result = ToolRegistry().execute(
        tool_name="send_whatsapp_message",
        payload={
            "phone": "+5492604000001",
            "message": "Tu pedido saldra hoy.",
        },
        context=ToolContext(run=run, user_id=str(user.id), is_staff=True),
    )
    approval = ApprovalRequest.objects.get(id=result["approval_request_id"])

    response = client.post(
        f"/api/v1/ai/approvals/{approval.id}/reject/",
        {"note": "No corresponde"},
        format="json",
    )

    approval.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert approval.status == ApprovalRequest.Status.REJECTED
    assert approval.approved_by_id == user.id
    assert approval.decision_note == "No corresponde"
    assert approval.workflow_run.status == WorkflowRun.Status.CANCELLED
    assert approval.action_payload["execution_status"] == "rejected"


@pytest.mark.django_db
def test_non_staff_cannot_decide_approvals(authenticated_client) -> None:
    """Approval decisions should stay staff-only."""
    client, _ = authenticated_client
    workflow = WorkflowRun.objects.create(
        workflow_type="manual_review",
        idempotency_key="workflow-deny-1",
    )
    approval = ApprovalRequest.objects.create(workflow_run=workflow, action_name="send_support_email", action_payload={"to": "cliente@example.com"})

    response = client.post(
        f"/api/v1/ai/approvals/{approval.id}/approve/",
        {"note": "No debería poder"},
        format="json",
    )

    approval.refresh_from_db()
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert approval.status == ApprovalRequest.Status.PENDING


@pytest.mark.django_db
def test_registry_blocks_high_risk_tool_and_marks_run_for_human() -> None:
    """High-risk tools should create an approval instead of executing immediately."""
    staff_user = UserFactory(is_staff=True)
    conversation = Conversation.objects.create(mode=Conversation.Mode.OPS, customer=staff_user)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.OPS)

    result = ToolRegistry().execute(
        tool_name="send_whatsapp_message",
        payload={"phone": "+5492604000009", "message": "Seguimos tu pedido."},
        context=ToolContext(run=run, user_id=str(staff_user.id), is_staff=True),
    )

    run.refresh_from_db()
    assert result["approval_required"] is True
    assert ApprovalRequest.objects.filter(id=result["approval_request_id"], action_name="send_whatsapp_message").exists()
    assert run.needs_human is True
    assert ToolExecution.objects.filter(run=run, status=ToolExecution.Status.BLOCKED, tool_name="send_whatsapp_message").exists()
