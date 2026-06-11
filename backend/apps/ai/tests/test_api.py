"""API tests for the AI app."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

from apps.ai.models import (
    ApprovalRequest,
    Conversation,
    KnowledgeSource,
    Lead,
    StockReservation,
    SupportTask,
    WorkflowRun,
)
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.authentication.tests.factories import UserFactory
from apps.catalog.tests.factories import WineFactory
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory


@pytest.fixture
def seeded_knowledge() -> KnowledgeSource:
    """Create a minimal public knowledge source for retrieval tests."""
    source = KnowledgeSource.objects.create(
        name="FAQ Seed",
        source_type=KnowledgeSource.SourceType.FAQ,
        uri="seed://faq",
    )
    KnowledgeIngestionService().upsert_document(
        source=source,
        external_id="shipping-faq",
        title="Envios y retiro",
        content=(
            "El retiro en bodega se coordina luego de la confirmacion.\n"
            "La cobertura prioritaria es Cuyo y AMBA."
        ),
    )
    return source


@pytest.mark.django_db
def test_chat_session_message_uses_knowledge_fallback(api_client, seeded_knowledge) -> None:
    """The support session should answer from the knowledge base when no live tool is needed."""
    del seeded_knowledge
    response = api_client.post(
        "/api/v1/ai/chat/sessions/",
        {"channel": "web", "mode": "support", "metadata": {}},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    conversation_id = response.data["id"]

    message_response = api_client.post(
        f"/api/v1/ai/chat/sessions/{conversation_id}/messages/",
        {"message": "Puedo retirar la compra en la bodega?"},
        format="json",
    )

    assert message_response.status_code == status.HTTP_200_OK
    assert "retiro en bodega" in message_response.data["assistant_turn"]["content"].lower()
    assert len(message_response.data["assistant_turn"]["citations"]) >= 1


@pytest.mark.django_db
def test_authenticated_customer_can_check_own_order_status(authenticated_client) -> None:
    """Authenticated customers should get their own order summary."""
    client, user = authenticated_client
    order = OrderFactory(
        user=user,
        order_number="LAB-2026-000145",
        status=Order.Status.PREPARING,
        total=Decimal("12400.00"),
    )
    del order
    response = client.post(
        "/api/v1/ai/chat/sessions/",
        {"channel": "web", "mode": "support", "metadata": {}},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    conversation_id = response.data["id"]

    message_response = client.post(
        f"/api/v1/ai/chat/sessions/{conversation_id}/messages/",
        {"message": "Quiero saber el estado de mi pedido LAB-2026-000145"},
        format="json",
    )

    assert message_response.status_code == status.HTTP_200_OK
    assert "lab-2026-000145" in message_response.data["assistant_turn"]["content"].lower()
    assert "preparando" in message_response.data["assistant_turn"]["content"].lower()


@pytest.mark.django_db
def test_staff_can_use_backoffice_copilot_for_low_stock(authenticated_client) -> None:
    """Staff users should be able to use the ops copilot endpoint."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    response = client.post(
        "/api/v1/ai/copilot/messages/",
        {"message": "Mostrame el stock bajo"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["conversation"]["mode"] == Conversation.Mode.OPS


@pytest.mark.django_db
def test_staff_can_create_knowledge_source(authenticated_client) -> None:
    """Staff users should manage knowledge sources via API."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    response = client.post(
        "/api/v1/ai/knowledge/sources/",
        {"name": "Manual Source", "source_type": "manual", "uri": "seed://manual"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Manual Source"


@pytest.mark.django_db
def test_chat_session_owned_by_customer_is_not_accessible_anonymously(api_client) -> None:
    """Anonymous users should not post into a customer-owned conversation."""
    user = UserFactory()
    conversation = Conversation.objects.create(customer=user, channel=Conversation.Channel.WEB)
    response = api_client.post(
        f"/api/v1/ai/chat/sessions/{conversation.id}/messages/",
        {"message": "hola"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_staff_can_fetch_copilot_overview_with_recent_artifacts(authenticated_client) -> None:
    """The backoffice should expose a compact overview for the Copilot page."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    workflow = WorkflowRun.objects.create(
        workflow_type="order_exception",
        status=WorkflowRun.Status.PENDING,
        actor_type="agent",
        input_payload={},
        result_payload={},
        idempotency_key="workflow-overview",
    )
    SupportTask.objects.create(
        task_type=SupportTask.TaskType.ORDER_ISSUE,
        title="Revisar despacho frenado",
        priority=SupportTask.Priority.HIGH,
        created_by=user,
        workflow_run=workflow,
    )
    Lead.objects.create(
        full_name="Lucia Gomez",
        email="lucia@example.com",
        source_channel=Conversation.Channel.WHATSAPP,
        created_by=user,
    )
    ApprovalRequest.objects.create(
        workflow_run=workflow,
        action_name="send_refund",
        action_payload={"order_number": "LAB-2026-000991"},
    )
    wine = WineFactory(sku="LAB-OVERVIEW-1")
    StockReservation.objects.create(
        wine=wine,
        quantity=4,
        customer=user,
        created_by=user,
        workflow_run=workflow,
        status=StockReservation.Status.ACTIVE,
    )
    ApprovalRequest.objects.create(
        workflow_run=workflow,
        action_name="request_order_cancellation",
        action_payload={"order_number": "LAB-2026-000145"},
    )

    response = client.get("/api/v1/ai/copilot/overview/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["metrics"]["open_tasks"] == 1
    assert response.data["metrics"]["new_leads"] == 1
    assert response.data["metrics"]["pending_approvals"] == 2
    assert response.data["metrics"]["active_stock_reservations"] == 1
    assert response.data["metrics"]["pending_cancellation_approvals"] == 1
    assert len(response.data["prompt_suggestions"]) >= 3
    assert response.data["recent_tasks"][0]["title"] == "Revisar despacho frenado"
    assert response.data["recent_stock_reservations"][0]["wine_sku"] == "LAB-OVERVIEW-1"
    assert (
        response.data["pending_cancellation_approvals"][0]["action_name"]
        == "request_order_cancellation"
    )


@pytest.mark.django_db
def test_staff_can_list_and_update_ai_tasks_and_leads(authenticated_client) -> None:
    """Staff users should be able to review and update AI-created operational records."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    task = SupportTask.objects.create(
        task_type=SupportTask.TaskType.SUPPORT_FOLLOW_UP,
        title="Llamar por seguimiento",
        status=SupportTask.Status.OPEN,
        priority=SupportTask.Priority.MEDIUM,
        created_by=user,
    )
    lead = Lead.objects.create(
        full_name="Martin Diaz",
        email="martin@example.com",
        status=Lead.Status.NEW,
        created_by=user,
    )

    task_list_response = client.get("/api/v1/ai/tasks/?status=open")
    lead_list_response = client.get("/api/v1/ai/leads/?status=new")
    task_update_response = client.patch(
        f"/api/v1/ai/tasks/{task.id}/",
        {"status": "in_progress", "priority": "high"},
        format="json",
    )
    lead_update_response = client.patch(
        f"/api/v1/ai/leads/{lead.id}/",
        {"status": "qualified", "interest_summary": "Busca propuesta corporativa."},
        format="json",
    )

    assert task_list_response.status_code == status.HTTP_200_OK
    assert lead_list_response.status_code == status.HTTP_200_OK
    assert task_list_response.data[0]["title"] == "Llamar por seguimiento"
    assert lead_list_response.data[0]["full_name"] == "Martin Diaz"
    assert task_update_response.status_code == status.HTTP_200_OK
    assert lead_update_response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    lead.refresh_from_db()
    assert task.status == SupportTask.Status.IN_PROGRESS
    assert task.priority == SupportTask.Priority.HIGH
    assert lead.status == Lead.Status.QUALIFIED


@pytest.mark.django_db
def test_staff_can_list_approval_queue(authenticated_client) -> None:
    """Staff users should be able to inspect the pending approval queue."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    workflow = WorkflowRun.objects.create(
        workflow_type="refund_flow",
        status=WorkflowRun.Status.PENDING,
        actor_type="agent",
        input_payload={},
        result_payload={},
        idempotency_key="workflow-approval-list",
    )
    ApprovalRequest.objects.create(
        workflow_run=workflow,
        action_name="refund_order",
        action_payload={"order_number": "LAB-2026-000992"},
    )

    response = client.get("/api/v1/ai/approvals/?status=pending")

    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["action_name"] == "refund_order"
    assert response.data[0]["workflow_type"] == "refund_flow"


@pytest.mark.django_db
def test_staff_can_fetch_single_approval_detail(authenticated_client) -> None:
    """Staff users should be able to inspect one approval inline from the Copilot."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    workflow = WorkflowRun.objects.create(
        workflow_type="tool_approval",
        status=WorkflowRun.Status.PENDING,
        actor_type="agent",
        input_payload={},
        result_payload={},
        idempotency_key="workflow-approval-detail",
    )
    approval = ApprovalRequest.objects.create(
        workflow_run=workflow,
        action_name="reserve_stock",
        action_payload={"sku": "LAB-RES-900", "quantity": 3},
    )

    response = client.get(f"/api/v1/ai/approvals/{approval.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(approval.id)
    assert response.data["action_name"] == "reserve_stock"
    assert response.data["workflow_type"] == "tool_approval"


@pytest.mark.django_db
def test_staff_can_list_stock_reservations(authenticated_client) -> None:
    """Staff users should be able to inspect AI-managed stock reservations."""
    client, user = authenticated_client
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    wine = WineFactory(sku="LAB-RES-API")
    reservation = StockReservation.objects.create(
        wine=wine,
        quantity=5,
        released_quantity=2,
        customer=user,
        created_by=user,
        status=StockReservation.Status.PARTIALLY_RELEASED,
        reason="Reserva de contingencia",
    )

    response = client.get(
        "/api/v1/ai/stock-reservations/?status=partially_released&search=contingencia"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["id"] == str(reservation.id)
    assert response.data[0]["wine_sku"] == "LAB-RES-API"
    assert response.data[0]["remaining_quantity"] == 3
