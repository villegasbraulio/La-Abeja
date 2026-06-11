"""Tests for operational and analytics AI tools."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.ai.models import AgentRun, Conversation, InternalNote, Lead, SupportTask, WorkflowRun
from apps.ai.tools.analytics_tools import (
    get_sales_by_bottle,
    get_sales_by_varietal,
    get_sales_over_period,
    get_sales_summary,
)
from apps.ai.tools.base import ToolContext
from apps.ai.tools.business_tools import (
    assign_order_issue,
    check_payment_issue,
    classify_customer_message,
    create_internal_note,
    create_lead_from_conversation,
    create_support_task,
    draft_whatsapp_reply,
    mark_order_for_review,
    recommend_wines_for_customer,
    send_support_email,
    send_whatsapp_message,
    update_lead_status,
    update_order_status,
    update_support_task,
)
from apps.authentication.tests.factories import UserFactory
from apps.catalog.models import Varietal
from apps.catalog.tests.factories import CategoryFactory, VarietalFactory, WineFactory
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory, OrderItemFactory
from apps.payments.models import Payment
from apps.payments.tests.factories import PaymentFactory


def _context(*, is_staff: bool = True, user=None, conversation=None) -> ToolContext:
    """Build a tool execution context for tests."""
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
def test_create_support_task_creates_task_and_workflow() -> None:
    """Support tasks should persist with workflow traceability."""
    customer = UserFactory(email="customer@example.com")
    conversation = Conversation.objects.create(customer=customer, mode=Conversation.Mode.OPS)
    context = _context(conversation=conversation)

    result = create_support_task(
        {
            "title": "Seguir consulta por demora",
            "description": "Contactar al cliente por una demora en despacho.",
            "task_type": "support_follow_up",
            "priority": "high",
            "conversation_id": str(conversation.id),
            "customer_email": customer.email,
            "due_in_days": 2,
        },
        context,
    )

    assert result["created"] is True
    task = SupportTask.objects.get(id=result["task_id"])
    assert task.title == "Seguir consulta por demora"
    assert task.priority == SupportTask.Priority.HIGH
    assert task.customer == customer
    assert task.workflow_run is not None
    assert WorkflowRun.objects.filter(
        id=task.workflow_run_id, workflow_type="create_support_task"
    ).exists()


@pytest.mark.django_db
def test_assign_order_issue_and_mark_order_for_review_create_internal_records() -> None:
    """Order issue and review tools should create tasks and notes."""
    context = _context()
    order = OrderFactory(order_number="LAB-2026-000701")

    issue_result = assign_order_issue(
        {
            "order_number": order.order_number,
            "issue_type": "tracking_missing",
            "summary": "El cliente no recibio tracking y reclama envio.",
            "priority": "urgent",
        },
        context,
    )
    review_result = mark_order_for_review(
        {
            "order_number": order.order_number,
            "reason": "Pago aprobado pero reclamo por direccion dudosa.",
        },
        context,
    )

    assert issue_result["created"] is True
    assert review_result["marked"] is True
    assert (
        SupportTask.objects.filter(order=order, task_type=SupportTask.TaskType.ORDER_ISSUE).count()
        == 1
    )
    assert (
        SupportTask.objects.filter(order=order, task_type=SupportTask.TaskType.ORDER_REVIEW).count()
        == 1
    )
    assert InternalNote.objects.filter(order=order).count() == 2


@pytest.mark.django_db
def test_create_internal_note_and_lead_from_conversation() -> None:
    """The AI layer should persist notes and commercial leads."""
    customer = UserFactory(email="lead@example.com", first_name="Lucia", last_name="Suarez")
    conversation = Conversation.objects.create(
        customer=customer, channel=Conversation.Channel.WHATSAPP
    )
    context = _context(conversation=conversation)

    note_result = create_internal_note(
        {
            "content": "Cliente interesado en cajas para regalo empresarial.",
            "note_type": "sales",
            "conversation_id": str(conversation.id),
            "customer_email": customer.email,
        },
        context,
    )
    lead_result = create_lead_from_conversation(
        {
            "conversation_id": str(conversation.id),
            "customer_email": customer.email,
            "company": "Bodega Partner",
            "interest_summary": "Busca 40 cajas con branding para fin de anio.",
            "desired_varietals": ["Malbec", "Blend"],
            "estimated_order_value": "350000.00",
        },
        context,
    )

    assert note_result["created"] is True
    assert lead_result["created"] is True
    assert InternalNote.objects.filter(
        conversation=conversation, note_type=InternalNote.NoteType.SALES
    ).exists()
    lead = Lead.objects.get(id=lead_result["lead_id"])
    assert lead.full_name == customer.full_name
    assert lead.desired_varietals == ["Malbec", "Blend"]


@pytest.mark.django_db
def test_classification_and_whatsapp_draft_cover_payment_issue() -> None:
    """Message classification and drafts should recognize payment-sensitive messages."""
    context = _context(is_staff=False)
    classification = classify_customer_message(
        {"message": "Hola, mi pago fue rechazado y necesito resolverlo hoy."},
        context,
    )
    draft = draft_whatsapp_reply(
        {
            "message": "Hola, mi pago fue rechazado y necesito resolverlo hoy.",
            "customer_name": "Sofia",
        },
        context,
    )

    assert classification["intent"] == "payment_issue"
    assert classification["should_escalate"] is True
    assert "Sofia" in draft["draft_text"]
    assert "pago" in draft["draft_text"].lower()


@pytest.mark.django_db
def test_recommend_wines_for_customer_uses_customer_preferences() -> None:
    """Recommendations should prefer the customer's favored varietals."""
    customer = UserFactory(email="winefan@example.com", preferred_varietals=["Malbec"])
    category = CategoryFactory()
    malbec = Varietal.objects.create(name="Malbec", slug="malbec")
    cabernet = Varietal.objects.create(name="Cabernet Sauvignon", slug="cabernet-sauvignon")
    WineFactory(
        category=category,
        varietal=malbec,
        name="Malbec Clasico",
        sku="LAB-MALBEC",
        price=Decimal("12000.00"),
    )
    WineFactory(
        category=category,
        varietal=cabernet,
        name="Cabernet Reserva",
        sku="LAB-CAB",
        price=Decimal("12500.00"),
    )
    context = _context(is_staff=False, user=customer)

    result = recommend_wines_for_customer(
        {"customer_email": customer.email, "limit": 2},
        context,
    )

    assert result["results"]
    assert result["results"][0]["varietal"] == "Malbec"
    assert "preferencia" in result["results"][0]["reason"]


@pytest.mark.django_db
def test_check_payment_issue_detects_stuck_paid_order() -> None:
    """Payment diagnostics should spot approved payments on non-advanced orders."""
    customer = UserFactory(email="payer@example.com")
    order = OrderFactory(
        user=customer,
        order_number="LAB-2026-000888",
        status=Order.Status.PENDING_PAYMENT,
        total=Decimal("15200.00"),
    )
    PaymentFactory(
        order=order,
        status=Payment.Status.APPROVED,
        status_detail="accredited",
        payment_method="visa",
        amount=order.total,
    )
    context = _context(is_staff=True)

    result = check_payment_issue({"order_number": order.order_number}, context)

    assert result["found"] is True
    assert result["diagnosis"] == "payment_approved_order_not_advanced"
    assert "actualizar" in result["recommended_action"].lower()


@pytest.mark.django_db
def test_update_support_task_and_lead_status_persist_changes() -> None:
    """Operators should be able to update lightweight operational artifacts."""
    assignee = UserFactory(email="ops@example.com", is_staff=True)
    context = _context()
    task_result = create_support_task(
        {
            "title": "Revisar reclamo por tracking",
            "task_type": "order_issue",
        },
        context,
    )
    lead_result = create_lead_from_conversation(
        {
            "full_name": "Lucia Suarez",
            "email": "lucia@example.com",
            "interest_summary": "Busca regalos empresariales.",
        },
        context,
    )

    task_update = update_support_task(
        {
            "task_id": task_result["task_id"],
            "status": "in_progress",
            "assigned_to_email": assignee.email,
            "append_note": "Tomado por operaciones.",
        },
        context,
    )
    lead_update = update_lead_status(
        {
            "lead_id": lead_result["lead_id"],
            "status": "qualified",
            "estimated_order_value": "240000.00",
        },
        context,
    )

    task = SupportTask.objects.get(id=task_result["task_id"])
    lead = Lead.objects.get(id=lead_result["lead_id"])
    assert task_update["updated"] is True
    assert task.status == SupportTask.Status.IN_PROGRESS
    assert task.assigned_to == assignee
    assert "Tomado por operaciones" in task.description
    assert lead_update["updated"] is True
    assert lead.status == Lead.Status.QUALIFIED
    assert lead.estimated_order_value == Decimal("240000.00")


@pytest.mark.django_db
def test_update_order_status_and_contact_tools_execute_side_effects(monkeypatch) -> None:
    """High-value handlers should change state and create internal notes when executed."""
    context = _context()
    customer = UserFactory(email="buyer@example.com", phone="+5492604000000")
    order = OrderFactory(
        user=customer, order_number="LAB-2026-000990", status=Order.Status.PREPARING
    )
    sent_whatsapp: list[tuple[str, str]] = []
    sent_emails: list[tuple[str, str, dict[str, object]]] = []

    monkeypatch.setattr(
        "apps.notifications.whatsapp.WhatsAppService.send_text",
        lambda to, text: sent_whatsapp.append((to, text)),
    )
    monkeypatch.setattr(
        "apps.notifications.email.EmailService.send_transactional",
        lambda to, template, context: sent_emails.append((to, template, context)),
    )

    order_result = update_order_status(
        {
            "order_number": order.order_number,
            "new_status": "shipped",
            "tracking_number": "AND-555",
            "note": "Despacho confirmado por Andreani.",
        },
        context,
    )
    whatsapp_result = send_whatsapp_message(
        {
            "order_number": order.order_number,
            "message": "Hola, tu pedido ya salio con tracking AND-555.",
        },
        context,
    )
    email_result = send_support_email(
        {
            "order_number": order.order_number,
            "message": "Tu pedido ya fue despachado. Te compartimos el tracking AND-555.",
        },
        context,
    )

    order.refresh_from_db()
    assert order_result["updated"] is True
    assert order.status == Order.Status.SHIPPED
    assert order.tracking_number == "AND-555"
    assert sent_whatsapp == [("+5492604000000", "Hola, tu pedido ya salio con tracking AND-555.")]
    assert whatsapp_result["sent"] is True
    assert sent_emails[0][0] == "buyer@example.com"
    assert email_result["sent"] is True
    assert InternalNote.objects.filter(order=order).count() == 3


@pytest.mark.django_db
def test_business_tools_return_clear_errors_for_missing_or_invalid_inputs() -> None:
    """Business tools should fail safely on bad payloads instead of mutating state."""
    staff_context = _context()
    customer_context = _context(is_staff=False)
    invalid_order = OrderFactory(order_number="LAB-2026-000999")

    assert create_support_task({}, staff_context)["error"] == "missing_title"
    assert create_lead_from_conversation({}, staff_context)["error"] == "missing_full_name"
    assert (
        update_support_task({"task_id": "00000000-0000-0000-0000-000000000000"}, staff_context)[
            "error"
        ]
        == "task_not_found"
    )
    assert (
        update_lead_status({"lead_id": "00000000-0000-0000-0000-000000000000"}, staff_context)[
            "error"
        ]
        == "lead_not_found"
    )
    assert (
        update_order_status(
            {"order_number": invalid_order.order_number, "new_status": "spaceship"}, staff_context
        )["error"]
        == "invalid_status"
    )
    assert send_whatsapp_message({"message": "hola"}, staff_context)["error"] == "missing_phone"
    assert send_support_email({"message": "hola"}, staff_context)["error"] == "missing_email"
    assert (
        create_support_task({"title": "No permitido"}, customer_context)["error"]
        == "staff_required"
    )
    assert (
        send_whatsapp_message({"phone": "+5492604000000", "message": "hola"}, customer_context)[
            "error"
        ]
        == "staff_required"
    )


@pytest.mark.django_db
def test_sales_tools_aggregate_summary_and_breakdowns() -> None:
    """Sales tools should compute totals and grouped metrics from paid orders."""
    category = CategoryFactory()
    malbec = VarietalFactory(name="Malbec", slug="malbec-sales")
    cabernet = VarietalFactory(name="Cabernet", slug="cabernet-sales")
    wine_malbec = WineFactory(
        category=category, varietal=malbec, name="Malbec Reserva", sku="LAB-MAL-1"
    )
    wine_cabernet = WineFactory(
        category=category, varietal=cabernet, name="Cabernet Estate", sku="LAB-CAB-1"
    )

    order_one = OrderFactory(
        status=Order.Status.PAID,
        total=Decimal("13500.00"),
        subtotal=Decimal("13500.00"),
        shipping_cost=Decimal("0.00"),
    )
    OrderItemFactory(
        order=order_one,
        wine=wine_malbec,
        wine_name=wine_malbec.name,
        wine_sku=wine_malbec.sku,
        quantity=2,
        unit_price=Decimal("4500.00"),
        subtotal=Decimal("9000.00"),
    )
    OrderItemFactory(
        order=order_one,
        wine=wine_cabernet,
        wine_name=wine_cabernet.name,
        wine_sku=wine_cabernet.sku,
        quantity=1,
        unit_price=Decimal("4500.00"),
        subtotal=Decimal("4500.00"),
    )

    order_two = OrderFactory(
        status=Order.Status.SHIPPED,
        total=Decimal("4500.00"),
        subtotal=Decimal("4500.00"),
        shipping_cost=Decimal("0.00"),
    )
    OrderItemFactory(
        order=order_two,
        wine=wine_malbec,
        wine_name=wine_malbec.name,
        wine_sku=wine_malbec.sku,
        quantity=1,
        unit_price=Decimal("4500.00"),
        subtotal=Decimal("4500.00"),
    )

    ignored_order = OrderFactory(status=Order.Status.PENDING_PAYMENT, total=Decimal("9999.00"))
    OrderItemFactory(
        order=ignored_order,
        wine=wine_malbec,
        wine_name=wine_malbec.name,
        wine_sku=wine_malbec.sku,
        quantity=10,
        unit_price=Decimal("999.90"),
        subtotal=Decimal("9999.00"),
    )

    context = _context()

    summary = get_sales_summary({"period": "last_30_days"}, context)
    over_period = get_sales_over_period({"period": "last_30_days", "grain": "day"}, context)
    varietals = get_sales_by_varietal({"period": "last_30_days"}, context)
    bottles = get_sales_by_bottle({"period": "last_30_days"}, context)

    assert summary["order_count"] == 2
    assert summary["total_revenue"] == "18000"
    assert summary["bottles_sold"] == 4
    assert over_period["results"]
    assert varietals["results"][0]["varietal"] == "Malbec"
    assert varietals["results"][0]["bottles_sold"] == 3
    assert bottles["results"][0]["sku"] == "LAB-MAL-1"
    assert bottles["results"][0]["bottles_sold"] == 3


@pytest.mark.django_db
def test_sales_tools_require_staff() -> None:
    """Sales analytics should stay restricted to staff contexts."""
    context = _context(is_staff=False)

    result = get_sales_summary({"period": "last_30_days"}, context)

    assert result["error"] == "staff_required"
