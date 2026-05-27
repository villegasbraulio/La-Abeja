"""API tests for the AI app."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

from apps.ai.models import Conversation, KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.authentication.tests.factories import UserFactory
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
