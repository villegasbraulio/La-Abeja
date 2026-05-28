"""Coverage for the newer AI operations, analytics, and knowledge tools."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.ai.models import AgentRun, Conversation, InternalNote, KnowledgeSource, StockReservation, SupportTask
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.ai.tools.analytics_tools import (
    get_conversion_funnel,
    get_margin_estimate_by_product,
    get_repeat_customers_metrics,
    get_returns_and_incidents_metrics,
    get_sales_by_channel,
    get_top_skus,
)
from apps.ai.tools.base import ToolContext
from apps.ai.tools.operations_tools import (
    create_payment_followup,
    create_restock_task,
    create_shipping_claim,
    create_ticket_and_assign,
    escalate_conversation_to_human,
    generate_shipping_update,
    get_customer_360,
    get_customer_orders_summary,
    release_stock_reservation,
    request_order_cancellation,
    reserve_stock,
    search_internal_notes,
    search_orders,
    sync_tracking_status,
)
from apps.ai.tools.knowledge_tools import get_answerable_sources, search_playbooks, search_policies
from apps.authentication.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory, VarietalFactory, WineFactory
from apps.orders.models import Cart, CartItem, Order
from apps.orders.tests.factories import OrderFactory, OrderItemFactory
from apps.payments.models import Payment
from apps.payments.tests.factories import PaymentFactory


def _shipping_address(*, source_channel: str) -> dict[str, str]:
    return {
        "recipient_name": "Maria Perez",
        "street": "Av. San Martin",
        "number": "1234",
        "floor_apt": "",
        "city": "San Rafael",
        "province": "Mendoza",
        "postal_code": "5600",
        "country": "Argentina",
        "phone": "+5492604000000",
        "source_channel": source_channel,
    }


def _context(*, is_staff: bool = True, user=None, conversation=None) -> ToolContext:
    actor = user or UserFactory(is_staff=is_staff)
    if is_staff and not actor.is_staff:
        actor.is_staff = True
        actor.save(update_fields=["is_staff"])
    active_conversation = conversation or Conversation.objects.create(
        customer=actor if not is_staff else None,
        mode=Conversation.Mode.OPS if is_staff else Conversation.Mode.SUPPORT,
    )
    run = AgentRun.objects.create(
        conversation=active_conversation,
        agent_type=AgentRun.AgentType.OPS if is_staff else AgentRun.AgentType.SUPPORT,
    )
    return ToolContext(run=run, user_id=str(actor.id), is_staff=is_staff)


@pytest.mark.django_db
def test_order_search_customer_views_and_note_search_cover_support_context() -> None:
    """Staff operators should be able to search orders and build customer context quickly."""
    customer = UserFactory(email="context@example.com", first_name="Ana", last_name="Lopez", phone="+5492604000002")
    conversation = Conversation.objects.create(customer=customer, mode=Conversation.Mode.OPS)
    staff_context = _context(conversation=conversation)
    order = OrderFactory(
        user=customer,
        order_number="LAB-2026-000401",
        status=Order.Status.SHIPPED,
        shipping_method=Order.ShippingMethod.EXPRESS,
        tracking_number="AND-401",
        shipping_address=_shipping_address(source_channel="whatsapp"),
    )
    PaymentFactory(order=order, status=Payment.Status.APPROVED, amount=order.total)
    SupportTask.objects.create(
        task_type=SupportTask.TaskType.ORDER_ISSUE,
        title="Seguimiento logistico",
        customer=customer,
        order=order,
        priority=SupportTask.Priority.HIGH,
    )
    note = InternalNote.objects.create(
        note_type=InternalNote.NoteType.ORDER,
        content="Cliente consulto por el tracking.",
        customer=customer,
        order=order,
    )

    search_result = search_orders({"customer_email": customer.email}, staff_context)
    summary_result = get_customer_orders_summary({"customer_email": customer.email}, staff_context)
    customer_360 = get_customer_360({"customer_email": customer.email}, staff_context)
    notes_result = search_internal_notes({"customer_email": customer.email, "query": "tracking"}, staff_context)
    shipping_draft = generate_shipping_update({"order_number": order.order_number}, staff_context)
    tracking_sync = sync_tracking_status({"order_number": order.order_number}, staff_context)

    assert search_result["results"][0]["order_number"] == order.order_number
    assert summary_result["order_count"] == 1
    assert customer_360["summary"]["open_task_count"] == 1
    assert customer_360["recent_notes"][0]["note_id"] == str(note.id)
    assert notes_result["results"][0]["note_id"] == str(note.id)
    assert shipping_draft["generated"] is True
    assert "AND-401" in shipping_draft["draft_text"]
    assert tracking_sync["carrier"] == "Andreani"


@pytest.mark.django_db
def test_new_operational_write_tools_create_tasks_and_escalations() -> None:
    """New low-risk write tools should create actionable operational artifacts."""
    customer = UserFactory(email="ops-context@example.com")
    assignee = UserFactory(email="ops-owner@example.com", is_staff=True)
    conversation = Conversation.objects.create(customer=customer, mode=Conversation.Mode.OPS)
    context = _context(conversation=conversation)
    low_stock_wine = WineFactory(stock=2, low_stock_threshold=8, sku="LAB-LOW-OPS")
    order = OrderFactory(user=customer, order_number="LAB-2026-000402", status=Order.Status.PAYMENT_FAILED)
    PaymentFactory(order=order, status=Payment.Status.REJECTED, amount=order.total, status_detail="cc_rejected_bad_filled_card_number")

    ticket = create_ticket_and_assign(
        {
            "summary": "Resolver reclamo operativo del pedido.",
            "order_number": order.order_number,
            "customer_email": customer.email,
            "assigned_to_email": assignee.email,
            "ticket_type": "order_issue",
        },
        context,
    )
    escalation = escalate_conversation_to_human(
        {
            "conversation_id": str(conversation.id),
            "reason": "Cliente insiste con una devolucion urgente.",
            "assigned_to_email": assignee.email,
        },
        context,
    )
    payment_followup = create_payment_followup({"order_number": order.order_number}, context)
    restock_task = create_restock_task({"sku": low_stock_wine.sku, "assigned_to_email": assignee.email}, context)
    shipping_claim = create_shipping_claim(
        {
            "order_number": order.order_number,
            "claim_reason": "tracking_missing",
            "summary": "El cliente no ve movimiento del despacho.",
        },
        context,
    )

    conversation.refresh_from_db()
    assert ticket["created"] is True
    assert escalation["escalated"] is True
    assert conversation.status == Conversation.Status.ESCALATED
    assert payment_followup["created"] is True
    assert restock_task["created"] is True
    assert shipping_claim["created"] is True
    assert SupportTask.objects.filter(assigned_to=assignee).count() >= 3


@pytest.mark.django_db
def test_stock_reservation_release_and_cancellation_handlers_mutate_state() -> None:
    """High-risk handler logic should reserve stock, release it, and cancel orders correctly."""
    customer = UserFactory(email="reserve@example.com")
    context = _context()
    wine = WineFactory(stock=12, sku="LAB-RES-1", name="Reserva Operativa")
    order = OrderFactory(user=customer, order_number="LAB-2026-000403", status=Order.Status.PENDING_PAYMENT)
    PaymentFactory(order=order, status=Payment.Status.APPROVED, amount=order.total)

    reserved = reserve_stock(
        {
            "sku": wine.sku,
            "quantity": 3,
            "order_number": order.order_number,
            "customer_email": customer.email,
            "reason": "Separar stock por contingencia de logistica.",
        },
        context,
    )
    wine.refresh_from_db()
    released = release_stock_reservation({"reservation_id": reserved["reservation_id"], "quantity": 2}, context)
    wine.refresh_from_db()
    cancelled = request_order_cancellation({"order_number": order.order_number, "reason": "Cliente pidio anular la compra."}, context)
    order.refresh_from_db()
    reservation = StockReservation.objects.get(id=reserved["reservation_id"])

    assert reserved["reserved"] is True
    assert wine.stock == 11
    assert released["released"] is True
    assert reservation.status == StockReservation.Status.PARTIALLY_RELEASED
    assert cancelled["cancelled"] is True
    assert order.status == Order.Status.CANCELLED
    assert cancelled["payment_followup_task_id"] is not None


@pytest.mark.django_db
def test_knowledge_specialized_search_and_advanced_metrics_work() -> None:
    """Knowledge specializations and advanced analytics should return structured business outputs."""
    source = KnowledgeSource.objects.create(
        name="AI Tooling Docs",
        source_type=KnowledgeSource.SourceType.MANUAL,
        uri="seed://tool-docs",
    )
    ingestion = KnowledgeIngestionService()
    ingestion.upsert_document(
        source=source,
        external_id="policy-shipping",
        title="Politica de envios",
        content="La politica de envios cubre Cuyo, AMBA y retiro en bodega.",
        channel="public",
    )
    ingestion.upsert_document(
        source=source,
        external_id="playbook-escalation",
        title="Playbook interno de escalaciones",
        content="Escalar casos urgentes al owner de operaciones con contexto del pedido.",
        channel="internal",
    )

    category = CategoryFactory()
    varietal = VarietalFactory(name="Malbec Analytics", slug="malbec-analytics")
    wine = WineFactory(
        category=category,
        varietal=varietal,
        sku="LAB-AN-1",
        name="Malbec Analitico",
        price=Decimal("10000.00"),
        cost_price=Decimal("4000.00"),
    )
    repeat_customer = UserFactory(email="repeat@example.com")
    order_one = OrderFactory(
        user=repeat_customer,
        status=Order.Status.PAID,
        total=Decimal("10000.00"),
        subtotal=Decimal("10000.00"),
        shipping_cost=Decimal("0.00"),
        shipping_address=_shipping_address(source_channel="web"),
    )
    OrderItemFactory(order=order_one, wine=wine, wine_name=wine.name, wine_sku=wine.sku, quantity=1, unit_price=Decimal("10000.00"), subtotal=Decimal("10000.00"))
    order_two = OrderFactory(
        user=repeat_customer,
        status=Order.Status.SHIPPED,
        total=Decimal("20000.00"),
        subtotal=Decimal("20000.00"),
        shipping_cost=Decimal("0.00"),
        shipping_address=_shipping_address(source_channel="whatsapp"),
    )
    OrderItemFactory(order=order_two, wine=wine, wine_name=wine.name, wine_sku=wine.sku, quantity=2, unit_price=Decimal("10000.00"), subtotal=Decimal("20000.00"))
    OrderFactory(status=Order.Status.REFUNDED, shipping_address=_shipping_address(source_channel="web"))
    OrderFactory(status=Order.Status.PAYMENT_FAILED, shipping_address=_shipping_address(source_channel="backoffice"))
    SupportTask.objects.create(task_type=SupportTask.TaskType.SHIPPING_CLAIM, title="Reclamo", priority=SupportTask.Priority.HIGH)

    cart = Cart.objects.create(user=repeat_customer)
    CartItem.objects.create(cart=cart, wine=wine, quantity=1, unit_price=wine.price)

    staff_context = _context()
    policy_result = search_policies({"query": "envios y retiro"}, staff_context)
    playbook_result = search_playbooks({"query": "casos urgentes"}, staff_context)
    sources_result = get_answerable_sources({"query": "retiro en bodega"}, staff_context)
    top_skus = get_top_skus({"period": "last_30_days"}, staff_context)
    repeat_metrics = get_repeat_customers_metrics({"period": "last_30_days"}, staff_context)
    funnel = get_conversion_funnel({"period": "last_30_days"}, staff_context)
    incidents = get_returns_and_incidents_metrics({"period": "last_30_days"}, staff_context)
    channels = get_sales_by_channel({"period": "last_30_days"}, staff_context)
    margins = get_margin_estimate_by_product({"period": "last_30_days"}, staff_context)

    assert policy_result["results"][0]["document_title"] == "Politica de envios"
    assert playbook_result["results"][0]["document_title"] == "Playbook interno de escalaciones"
    assert sources_result["sources"][0]["document_title"] == "Politica de envios"
    assert top_skus["results"][0]["sku"] == "LAB-AN-1"
    assert repeat_metrics["repeat_customers"] == 1
    assert funnel["cart_count"] >= 1
    assert incidents["payment_failed_orders"] >= 1
    assert {row["channel"] for row in channels["results"]} >= {"web", "whatsapp"}
    assert margins["results"][0]["estimated_margin"] == "18000"
