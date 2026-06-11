"""Operational and commercial tools for the AI layer."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.ai.models import Conversation, InternalNote, Lead, SupportTask, WorkflowRun
from apps.catalog.models import Wine
from apps.notifications.email import EmailService
from apps.notifications.whatsapp import WhatsAppService
from apps.orders.models import Order
from apps.payments.models import Payment

from .base import ToolContext

User = get_user_model()


def create_support_task(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create an internal support or operations task."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    title = str(payload.get("title") or "").strip()
    if not title:
        return {"created": False, "error": "missing_title"}

    task_type = _normalize_choice(
        value=payload.get("task_type"),
        allowed={choice for choice, _ in SupportTask.TaskType.choices},
        default=SupportTask.TaskType.SUPPORT_FOLLOW_UP,
    )
    priority = _normalize_choice(
        value=payload.get("priority"),
        allowed={choice for choice, _ in SupportTask.Priority.choices},
        default=SupportTask.Priority.MEDIUM,
    )
    if task_type is None or priority is None:
        return {"created": False, "error": "invalid_choice"}

    order = _resolve_order(payload.get("order_number"))
    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    customer = _resolve_customer(payload.get("customer_email"), conversation=conversation)
    assigned_to = _resolve_staff_user(payload.get("assigned_to_email"))
    due_at = _parse_due_at(payload)

    workflow_run = _create_workflow_run(
        context=context, workflow_type="create_support_task", payload=payload
    )
    task = SupportTask.objects.create(
        task_type=task_type,
        title=title,
        description=str(payload.get("description") or "").strip(),
        priority=priority,
        order=order,
        conversation=conversation,
        customer=customer,
        assigned_to=assigned_to,
        created_by=_actor_from_context(context),
        workflow_run=workflow_run,
        due_at=due_at,
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    workflow_run.result_payload = {"task_id": str(task.id), "status": task.status}
    workflow_run.status = WorkflowRun.Status.COMPLETED
    workflow_run.save(update_fields=["result_payload", "status", "updated_at"])

    return {
        "created": True,
        "task_id": str(task.id),
        "task_type": task.task_type,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "assigned_to": assigned_to.email if assigned_to else None,
        "order_number": order.order_number if order else None,
        "customer_email": customer.email if customer else None,
        "due_at": task.due_at.isoformat() if task.due_at else None,
    }


def create_internal_note(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Persist an internal note linked to a customer, order, or conversation."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    content = str(payload.get("content") or "").strip()
    if not content:
        return {"created": False, "error": "missing_content"}

    note_type = _normalize_choice(
        value=payload.get("note_type"),
        allowed={choice for choice, _ in InternalNote.NoteType.choices},
        default=InternalNote.NoteType.GENERAL,
    )
    if note_type is None:
        return {"created": False, "error": "invalid_note_type"}

    order = _resolve_order(payload.get("order_number"))
    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    customer = _resolve_customer(payload.get("customer_email"), conversation=conversation)

    note = InternalNote.objects.create(
        note_type=note_type,
        content=content,
        order=order,
        conversation=conversation,
        customer=customer,
        created_by=_actor_from_context(context),
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    return {
        "created": True,
        "note_id": str(note.id),
        "note_type": note.note_type,
        "order_number": order.order_number if order else None,
        "customer_email": customer.email if customer else None,
    }


def assign_order_issue(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create an order-issue task for internal follow-up."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    if order is None:
        return {"created": False, "error": "order_not_found"}

    issue_type = str(payload.get("issue_type") or "operational_issue").strip()
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        return {"created": False, "error": "missing_summary"}

    result = create_support_task(
        {
            "task_type": SupportTask.TaskType.ORDER_ISSUE,
            "priority": payload.get("priority") or SupportTask.Priority.HIGH,
            "title": f"{order.order_number} · {issue_type.replace('_', ' ')}",
            "description": summary,
            "order_number": order.order_number,
            "assigned_to_email": payload.get("assigned_to_email"),
            "customer_email": order.user.email,
        },
        context,
    )
    if not result.get("created"):
        return result

    create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER,
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "content": f"Issue assigned by AI tool: {summary}",
        },
        context,
    )
    result["issue_type"] = issue_type
    return result


def mark_order_for_review(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Mark an order for manual review by creating a high-priority task and note."""
    if not context.is_staff:
        return {"marked": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    if order is None:
        return {"marked": False, "error": "order_not_found"}

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        return {"marked": False, "error": "missing_reason"}

    task_result = create_support_task(
        {
            "task_type": SupportTask.TaskType.ORDER_REVIEW,
            "priority": payload.get("priority") or SupportTask.Priority.URGENT,
            "title": f"Review manual · {order.order_number}",
            "description": reason,
            "order_number": order.order_number,
            "customer_email": order.user.email,
        },
        context,
    )
    if not task_result.get("created"):
        return {"marked": False, **task_result}

    note_result = create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER,
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "content": f"Order marked for review: {reason}",
        },
        context,
    )
    return {
        "marked": True,
        "order_number": order.order_number,
        "task_id": task_result.get("task_id"),
        "note_id": note_result.get("note_id"),
        "reason": reason,
    }


def create_lead_from_conversation(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Create a commercial lead from a conversation or manual input."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    customer = _resolve_customer(payload.get("customer_email"), conversation=conversation)
    full_name = str(payload.get("full_name") or "").strip() or (
        customer.full_name if customer else ""
    )
    if not full_name:
        return {"created": False, "error": "missing_full_name"}

    estimated_order_value = _parse_decimal(payload.get("estimated_order_value"))
    desired_varietals = _normalize_string_list(payload.get("desired_varietals"))
    lead = Lead.objects.create(
        full_name=full_name,
        email=str(payload.get("email") or (customer.email if customer else "")).strip().lower(),
        phone=str(payload.get("phone") or (customer.phone if customer else "")).strip(),
        company=str(payload.get("company") or "").strip(),
        source_channel=conversation.channel
        if conversation
        else str(payload.get("source_channel") or Conversation.Channel.WEB),
        interest_summary=str(payload.get("interest_summary") or "").strip(),
        desired_varietals=desired_varietals,
        estimated_order_value=estimated_order_value,
        conversation=conversation,
        customer=customer,
        created_by=_actor_from_context(context),
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    return {
        "created": True,
        "lead_id": str(lead.id),
        "full_name": lead.full_name,
        "email": lead.email,
        "status": lead.status,
        "source_channel": lead.source_channel,
    }


def update_support_task(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Update a previously created AI task."""
    if not context.is_staff:
        return {"updated": False, "error": "staff_required"}

    task = _resolve_support_task(payload.get("task_id"))
    if task is None:
        return {"updated": False, "error": "task_not_found"}

    status_value = _normalize_choice(
        value=payload.get("status"),
        allowed={choice for choice, _ in SupportTask.Status.choices},
        default=task.status,
    )
    priority_value = _normalize_choice(
        value=payload.get("priority"),
        allowed={choice for choice, _ in SupportTask.Priority.choices},
        default=task.priority,
    )
    if status_value is None or priority_value is None:
        return {"updated": False, "error": "invalid_choice"}

    task.status = status_value
    task.priority = priority_value
    assigned_to = _resolve_staff_user(payload.get("assigned_to_email"))
    if payload.get("assigned_to_email") not in (None, ""):
        task.assigned_to = assigned_to

    due_at = _parse_due_at(payload)
    if payload.get("due_at") not in (None, "") or payload.get("due_in_days") not in (None, ""):
        task.due_at = due_at

    append_note = str(payload.get("append_note") or "").strip()
    if append_note:
        task.description = _append_text_block(task.description, append_note)

    task.metadata = {**task.metadata, "last_updated_by_run_id": str(context.run.id)}
    task.save(
        update_fields=[
            "status",
            "priority",
            "assigned_to",
            "due_at",
            "description",
            "metadata",
            "updated_at",
        ]
    )
    return {
        "updated": True,
        "task_id": str(task.id),
        "status": task.status,
        "priority": task.priority,
        "assigned_to": task.assigned_to.email if task.assigned_to else None,
        "due_at": task.due_at.isoformat() if task.due_at else None,
    }


def update_lead_status(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Update the status or commercial detail of an AI-captured lead."""
    if not context.is_staff:
        return {"updated": False, "error": "staff_required"}

    lead = _resolve_lead(payload.get("lead_id"))
    if lead is None:
        return {"updated": False, "error": "lead_not_found"}

    status_value = _normalize_choice(
        value=payload.get("status"),
        allowed={choice for choice, _ in Lead.Status.choices},
        default=lead.status,
    )
    if status_value is None:
        return {"updated": False, "error": "invalid_status"}

    lead.status = status_value
    if payload.get("interest_summary") not in (None, ""):
        lead.interest_summary = str(payload.get("interest_summary") or "").strip()
    estimated_order_value = _parse_decimal(payload.get("estimated_order_value"))
    if payload.get("estimated_order_value") not in (None, ""):
        lead.estimated_order_value = estimated_order_value

    lead.metadata = {**lead.metadata, "last_updated_by_run_id": str(context.run.id)}
    lead.save(
        update_fields=[
            "status",
            "interest_summary",
            "estimated_order_value",
            "metadata",
            "updated_at",
        ]
    )
    return {
        "updated": True,
        "lead_id": str(lead.id),
        "status": lead.status,
        "estimated_order_value": str(lead.estimated_order_value)
        if lead.estimated_order_value is not None
        else None,
    }


def update_order_status(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Update an order state and append an internal audit note."""
    if not context.is_staff:
        return {"updated": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    if order is None:
        return {"updated": False, "error": "order_not_found"}

    status_value = _normalize_choice(
        value=payload.get("new_status"),
        allowed={choice for choice, _ in Order.Status.choices},
        default=order.status,
    )
    if status_value is None:
        return {"updated": False, "error": "invalid_status"}

    previous_status = order.status
    order.status = status_value

    tracking_number = str(payload.get("tracking_number") or "").strip()
    if tracking_number:
        order.tracking_number = tracking_number

    estimated_delivery = _parse_date(payload.get("estimated_delivery"))
    if payload.get("estimated_delivery") not in (None, ""):
        order.estimated_delivery = estimated_delivery

    note = str(payload.get("note") or "").strip()
    if note:
        order.notes = _append_text_block(order.notes, f"[AI] {note}")

    if status_value == Order.Status.SHIPPED and order.shipped_at is None:
        order.shipped_at = timezone.now()
    if status_value == Order.Status.DELIVERED and order.delivered_at is None:
        order.delivered_at = timezone.now()

    order.save(
        update_fields=[
            "status",
            "tracking_number",
            "estimated_delivery",
            "notes",
            "shipped_at",
            "delivered_at",
            "updated_at",
        ]
    )
    note_record = InternalNote.objects.create(
        note_type=InternalNote.NoteType.ORDER,
        content=(
            f"Order status updated by AI approval from {previous_status} to {order.status}."
            + (f" Detail: {note}" if note else "")
        ),
        order=order,
        customer=order.user,
        created_by=_actor_from_context(context),
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    return {
        "updated": True,
        "order_number": order.order_number,
        "previous_status": previous_status,
        "status": order.status,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.estimated_delivery.isoformat()
        if order.estimated_delivery
        else None,
        "note_id": str(note_record.id),
    }


def send_whatsapp_message(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Send a WhatsApp message to a resolved recipient and persist an internal note."""
    if not context.is_staff:
        return {"sent": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    customer = _resolve_customer(
        payload.get("customer_email"),
        conversation=_resolve_conversation(payload.get("conversation_id"), context=context),
    )
    phone = _resolve_phone_number(payload.get("phone"), order=order, customer=customer)
    if not phone:
        return {"sent": False, "error": "missing_phone"}

    message = str(payload.get("message") or "").strip()
    template = str(payload.get("template") or "").strip()
    params = _normalize_string_list(payload.get("params"))
    if not message and not template:
        return {"sent": False, "error": "missing_message"}

    if template:
        WhatsAppService.send_template(phone, template, params)
    else:
        WhatsAppService.send_text(phone, message)

    note = InternalNote.objects.create(
        note_type=InternalNote.NoteType.SUPPORT,
        content=f"WhatsApp sent to {phone}. "
        + (f"Template: {template}." if template else f"Message: {message}"),
        order=order,
        customer=customer or (order.user if order else None),
        conversation=_resolve_conversation(payload.get("conversation_id"), context=context),
        created_by=_actor_from_context(context),
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    return {
        "sent": True,
        "channel": "whatsapp",
        "to": phone,
        "template": template or None,
        "message": message or None,
        "order_number": order.order_number if order else None,
        "note_id": str(note.id),
    }


def send_support_email(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Send a support or commercial email and persist an internal note."""
    if not context.is_staff:
        return {"sent": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    customer = _resolve_customer(
        payload.get("customer_email"),
        conversation=_resolve_conversation(payload.get("conversation_id"), context=context),
    )
    recipient = _resolve_email_address(payload.get("to"), order=order, customer=customer)
    if not recipient:
        return {"sent": False, "error": "missing_email"}

    message = str(payload.get("message") or "").strip()
    if not message:
        return {"sent": False, "error": "missing_message"}

    template = (
        str(payload.get("template") or "ai_support_follow_up").strip() or "ai_support_follow_up"
    )
    subject_hint = str(payload.get("subject_hint") or "").strip()
    EmailService.send_transactional(
        to=recipient,
        template=template,
        context={
            "subject_hint": subject_hint or "Seguimiento desde La Abeja",
            "message": message,
            "order_number": order.order_number if order else "",
        },
    )
    note = InternalNote.objects.create(
        note_type=InternalNote.NoteType.SUPPORT,
        content=f"Email sent to {recipient}. Message: {message}",
        order=order,
        customer=customer or (order.user if order else None),
        conversation=_resolve_conversation(payload.get("conversation_id"), context=context),
        created_by=_actor_from_context(context),
        metadata={"source": "ai_tool", "run_id": str(context.run.id), "template": template},
    )
    return {
        "sent": True,
        "channel": "email",
        "to": recipient,
        "template": template,
        "order_number": order.order_number if order else None,
        "note_id": str(note.id),
    }


def classify_customer_message(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Classify a support message with deterministic business heuristics."""
    del context
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"classified": False, "error": "missing_message"}

    normalized = message.lower()
    intent = "general_support"
    suggested_team = "support"
    urgency = "normal"
    sentiment = "neutral"
    entities: dict[str, object] = {}

    if "lab-" in normalized:
        intent = "order_status"
        entities["has_order_number"] = True
    elif any(keyword in normalized for keyword in ["envio", "retiro", "delivery", "despacho"]):
        intent = "shipping_question"
    elif any(keyword in normalized for keyword in ["pago", "tarjeta", "mercado pago", "cuotas"]):
        intent = "payment_issue"
        suggested_team = "payments"
    elif any(keyword in normalized for keyword in ["corporativo", "empresa", "regalo", "evento"]):
        intent = "corporate_sales"
        suggested_team = "sales"
    elif any(keyword in normalized for keyword in ["visita", "degustacion", "bodega", "reserva"]):
        intent = "booking_question"
        suggested_team = "hospitality"
    elif any(keyword in normalized for keyword in ["recomenda", "suger", "marid", "vino"]):
        intent = "product_recommendation"
        suggested_team = "sales"

    if any(keyword in normalized for keyword in ["urgente", "ya", "hoy", "ahora", "inmediato"]):
        urgency = "high"
    if any(
        keyword in normalized for keyword in ["enoj", "mal", "reclamo", "devolucion", "cancelar"]
    ):
        sentiment = "negative"
        urgency = "high" if urgency == "normal" else urgency

    return {
        "classified": True,
        "intent": intent,
        "urgency": urgency,
        "sentiment": sentiment,
        "suggested_team": suggested_team,
        "entities": entities,
        "should_escalate": urgency == "high" or intent in {"payment_issue", "corporate_sales"},
    }


def draft_whatsapp_reply(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Draft a WhatsApp-style reply without sending it."""
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"drafted": False, "error": "missing_message"}

    customer_name = str(payload.get("customer_name") or "").strip()
    classification = classify_customer_message(
        {"message": message},
        ToolContext(run=context.run, user_id=context.user_id, is_staff=context.is_staff),
    )
    greeting = f"Hola {customer_name}," if customer_name else "Hola,"
    intent = str(classification.get("intent") or "general_support")

    if intent == "order_status":
        body = (
            "gracias por escribirnos. Si me compartis el numero de pedido, "
            "te ayudo a revisar el estado enseguida."
        )
    elif intent == "shipping_question":
        body = (
            "gracias por tu consulta. Puedo ayudarte con opciones de envio o retiro "
            "en bodega segun tu pedido."
        )
    elif intent == "payment_issue":
        body = (
            "veo que tu consulta es sobre el pago. Si me compartis el numero de pedido "
            "o comprobante, lo revisamos con prioridad."
        )
    elif intent == "corporate_sales":
        body = (
            "gracias por contactarnos. Podemos ayudarte con regalos corporativos "
            "y propuestas para eventos."
        )
    elif intent == "product_recommendation":
        body = (
            "feliz de ayudarte a elegir un vino. Si me contas presupuesto, varietal "
            "o para que ocasion es, te recomiendo opciones concretas."
        )
    else:
        body = (
            "gracias por escribirnos. Contame un poco mas y te ayudo a resolverlo lo antes posible."
        )

    closing = "Quedo atento."
    return {
        "drafted": True,
        "intent": intent,
        "draft_text": f"{greeting} {body} {closing}".strip(),
        "should_escalate": bool(classification.get("should_escalate")),
    }


def recommend_wines_for_customer(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Recommend wines from catalog data and optional customer preferences."""
    del context
    customer = _resolve_customer(payload.get("customer_email"))
    preferred_varietals = _normalize_string_list(payload.get("preferred_varietals"))
    if not preferred_varietals and customer is not None:
        preferred_varietals = _normalize_string_list(customer.preferred_varietals)

    limit = max(1, min(int(payload.get("limit") or 4), 10))
    max_price = _parse_decimal(payload.get("max_price"))
    min_price = _parse_decimal(payload.get("min_price"))

    queryset = Wine.objects.select_related("category", "varietal").filter(
        is_active=True, stock__gt=0
    )
    if preferred_varietals:
        varietal_query = Q()
        for varietal_name in preferred_varietals:
            varietal_query |= Q(varietal__name__icontains=varietal_name)
        queryset = queryset.filter(varietal_query)
    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)

    wines = list(queryset.order_by("-is_featured", "-is_limited_edition", "price", "name")[:limit])
    return {
        "results": [
            {
                "id": str(wine.id),
                "name": wine.name,
                "sku": wine.sku,
                "varietal": wine.varietal.name,
                "category": wine.category.name,
                "price": str(wine.price),
                "stock": wine.stock,
                "reason": _build_recommendation_reason(
                    wine=wine, preferred_varietals=preferred_varietals
                ),
            }
            for wine in wines
        ]
    }


def check_payment_issue(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Inspect a payment and describe the likely operational issue."""
    payment = _resolve_payment(payload, context=context)
    if payment is None:
        return {"found": False, "error": "payment_not_found"}

    diagnosis = "payment_pending"
    recommendation = "Esperar la confirmacion o validar el webhook antes de contactar al cliente."
    if payment.status == Payment.Status.APPROVED and payment.order.status in {
        Order.Status.PAID,
        Order.Status.PREPARING,
        Order.Status.READY_TO_SHIP,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    }:
        diagnosis = "payment_ok"
        recommendation = "No hace falta intervenir. El pedido ya avanzo correctamente."
    elif (
        payment.status == Payment.Status.APPROVED
        and payment.order.status == Order.Status.PENDING_PAYMENT
    ):
        diagnosis = "payment_approved_order_not_advanced"
        recommendation = (
            "Revisar integracion de pagos y actualizar el pedido manualmente si corresponde."
        )
    elif payment.status == Payment.Status.REJECTED:
        diagnosis = "payment_rejected"
        recommendation = (
            "Pedir un nuevo intento de pago o validar el motivo de rechazo con el cliente."
        )
    elif payment.status == Payment.Status.CANCELLED:
        diagnosis = "payment_cancelled"
        recommendation = "Confirmar si el cliente desea reactivar la compra."
    elif payment.status == Payment.Status.REFUNDED:
        diagnosis = "payment_refunded"
        recommendation = "No cobrar nuevamente sin una confirmacion explicita del cliente."
    elif payment.status == Payment.Status.IN_PROCESS:
        diagnosis = "payment_in_process"
        recommendation = "Monitorear la acreditacion antes de preparar el pedido."

    return {
        "found": True,
        "order_number": payment.order.order_number,
        "payment_status": payment.status,
        "payment_status_detail": payment.status_detail,
        "payment_method": payment.payment_method,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "order_status": payment.order.status,
        "diagnosis": diagnosis,
        "recommended_action": recommendation,
    }


def _normalize_choice(*, value: object, allowed: set[str], default: str) -> str | None:
    if value in (None, ""):
        return default
    normalized = str(value).strip().lower()
    return normalized if normalized in allowed else None


def _resolve_order(order_number: object) -> Order | None:
    normalized = str(order_number or "").strip()
    if not normalized:
        return None
    return (
        Order.objects.select_related("user", "payment")
        .filter(order_number__iexact=normalized)
        .first()
    )


def _resolve_support_task(task_id: object) -> SupportTask | None:
    normalized = str(task_id or "").strip()
    if not normalized:
        return None
    return (
        SupportTask.objects.select_related("order", "customer", "assigned_to")
        .filter(id=normalized)
        .first()
    )


def _resolve_lead(lead_id: object) -> Lead | None:
    normalized = str(lead_id or "").strip()
    if not normalized:
        return None
    return Lead.objects.select_related("customer", "conversation").filter(id=normalized).first()


def _resolve_conversation(
    conversation_id: object, *, context: ToolContext | None = None
) -> Conversation | None:
    normalized = str(conversation_id or "").strip()
    if not normalized:
        return context.run.conversation if context is not None else None
    return Conversation.objects.filter(id=normalized).first()


def _resolve_customer(customer_email: object, *, conversation: Conversation | None = None):
    if conversation and conversation.customer_id:
        return conversation.customer
    normalized = str(customer_email or "").strip().lower()
    if not normalized:
        return None
    return User.objects.filter(email__iexact=normalized).first()


def _resolve_staff_user(email: object):
    normalized = str(email or "").strip().lower()
    if not normalized:
        return None
    return User.objects.filter(email__iexact=normalized, is_staff=True).first()


def _parse_due_at(payload: dict[str, object]) -> datetime | None:
    due_at_raw = str(payload.get("due_at") or "").strip()
    if due_at_raw:
        try:
            parsed = datetime.fromisoformat(due_at_raw)
        except ValueError:
            parsed = None
        if parsed is not None:
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed

    due_in_days = payload.get("due_in_days")
    if due_in_days in (None, ""):
        return None
    try:
        return timezone.now() + timedelta(days=int(due_in_days))
    except (TypeError, ValueError):
        return None


def _actor_from_context(context: ToolContext):
    if not context.user_id:
        return None
    return User.objects.filter(id=context.user_id).first()


def _create_workflow_run(
    *, context: ToolContext, workflow_type: str, payload: dict[str, object]
) -> WorkflowRun:
    return WorkflowRun.objects.create(
        workflow_type=workflow_type,
        status=WorkflowRun.Status.RUNNING,
        actor_type="staff" if context.is_staff else "agent",
        input_payload=payload,
        idempotency_key=f"{workflow_type}:{context.run.id}:{uuid4()}",
    )


def _normalize_string_list(raw_value: object) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        items: Iterable[str] = [part.strip() for part in raw_value.split(",")]
    elif isinstance(raw_value, list | tuple | set):
        items = [str(item).strip() for item in raw_value]
    else:
        return []
    return [item for item in items if item]


def _parse_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _append_text_block(existing: str, addition: str) -> str:
    normalized_existing = existing.strip()
    if not normalized_existing:
        return addition
    return f"{normalized_existing}\n{addition}"


def _build_recommendation_reason(*, wine: Wine, preferred_varietals: list[str]) -> str:
    matched_varietal = any(
        item.lower() in wine.varietal.name.lower() for item in preferred_varietals
    )
    reasons = []
    if matched_varietal:
        reasons.append(f"coincide con la preferencia por {wine.varietal.name}")
    if wine.is_featured:
        reasons.append("es una etiqueta destacada")
    if wine.is_limited_edition:
        reasons.append("tiene perfil de edicion limitada")
    if not reasons:
        reasons.append("tiene stock disponible y buena relacion catalogo-precio")
    return ", ".join(reasons)


def _resolve_payment(payload: dict[str, object], *, context: ToolContext) -> Payment | None:
    queryset = Payment.objects.select_related("order", "order__user")
    if not context.is_staff:
        if context.user_id is None:
            return None
        queryset = queryset.filter(order__user_id=context.user_id)

    order_number = str(payload.get("order_number") or "").strip()
    mp_payment_id = str(payload.get("mp_payment_id") or "").strip()
    if order_number:
        return queryset.filter(order__order_number__iexact=order_number).first()
    if mp_payment_id:
        return queryset.filter(mp_payment_id__iexact=mp_payment_id).first()
    return None


def _resolve_phone_number(phone: object, *, order: Order | None = None, customer=None) -> str:
    normalized = str(phone or "").strip()
    if normalized:
        return normalized
    if customer is not None and getattr(customer, "phone", ""):
        return str(customer.phone).strip()
    if order is not None and getattr(order.user, "phone", ""):
        return str(order.user.phone).strip()
    return ""


def _resolve_email_address(address: object, *, order: Order | None = None, customer=None) -> str:
    normalized = str(address or "").strip().lower()
    if normalized:
        return normalized
    if customer is not None and getattr(customer, "email", ""):
        return str(customer.email).strip().lower()
    if order is not None and getattr(order.user, "email", ""):
        return str(order.user.email).strip().lower()
    return ""
