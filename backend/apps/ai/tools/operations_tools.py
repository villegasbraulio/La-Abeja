"""Operational search and workflow tools for the AI layer."""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.ai.models import Conversation, InternalNote, Lead, StockReservation, SupportTask
from apps.catalog.models import Wine
from apps.orders.models import Order
from apps.orders.state_machine import can_transition
from apps.payments.models import Payment

from .base import ToolContext
from .business_tools import (
    _actor_from_context,
    _append_text_block,
    _normalize_string_list,
    _parse_date,
    _resolve_conversation,
    _resolve_customer,
    _resolve_order,
    _resolve_payment,
    check_payment_issue,
    create_internal_note,
    create_support_task,
)

COMPLETED_ORDER_STATUSES = {
    Order.Status.PAID,
    Order.Status.PREPARING,
    Order.Status.READY_TO_SHIP,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
}
OPEN_TASK_STATUSES = {
    SupportTask.Status.OPEN,
    SupportTask.Status.IN_PROGRESS,
    SupportTask.Status.BLOCKED,
}


def search_orders(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search orders by customer, status, date window, or free text."""
    queryset = Order.objects.select_related("user", "payment").prefetch_related("items")
    if not context.is_staff:
        if context.user_id is None:
            return {"results": [], "error": "authentication_required"}
        queryset = queryset.filter(user_id=context.user_id)

    query = str(payload.get("query") or "").strip()
    customer_email = str(payload.get("customer_email") or "").strip().lower()
    phone = str(payload.get("phone") or "").strip()
    status_values = _normalize_status_filters(payload)
    start_date, end_date = _resolve_date_range(payload)
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)

    if query:
        queryset = queryset.filter(
            Q(order_number__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(tracking_number__icontains=query)
        )
    if customer_email:
        queryset = queryset.filter(user__email__iexact=customer_email)
    if phone:
        queryset = queryset.filter(user__phone__icontains=phone)
    if status_values:
        queryset = queryset.filter(status__in=status_values)
    if start_date is not None:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date is not None:
        queryset = queryset.filter(created_at__date__lte=end_date)

    orders = list(queryset.order_by("-created_at")[:limit])
    return {
        "results": [_serialize_order(order) for order in orders],
        "filters": {
            "query": query or None,
            "customer_email": customer_email or None,
            "phone": phone or None,
            "statuses": status_values,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }


def get_customer_360(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return a staff-facing 360 snapshot for one customer."""
    if not context.is_staff:
        return {"found": False, "error": "staff_required"}

    customer = _resolve_target_customer(payload, context=context)
    if customer is None:
        return {"found": False, "error": "customer_not_found"}

    all_orders = (
        Order.objects.filter(user=customer).select_related("payment").prefetch_related("items")
    )
    completed_orders = all_orders.filter(status__in=COMPLETED_ORDER_STATUSES)
    revenue = completed_orders.aggregate(total=Sum("total")).get("total")
    last_order = all_orders.order_by("-created_at").first()
    last_completed = completed_orders.order_by("-created_at").first()
    open_tasks = SupportTask.objects.filter(
        customer=customer, status__in=OPEN_TASK_STATUSES
    ).select_related("order", "assigned_to")[:5]
    recent_notes = InternalNote.objects.filter(customer=customer).select_related(
        "order", "created_by"
    )[:5]
    recent_leads = Lead.objects.filter(customer=customer).order_by("-created_at")[:3]

    return {
        "found": True,
        "customer": {
            "email": customer.email,
            "full_name": customer.full_name,
            "phone": customer.phone,
            "preferred_varietals": list(customer.preferred_varietals or []),
            "newsletter_subscribed": customer.newsletter_subscribed,
            "date_joined": customer.date_joined.isoformat() if customer.date_joined else None,
        },
        "summary": {
            "order_count": all_orders.count(),
            "completed_order_count": completed_orders.count(),
            "total_revenue": str(revenue or 0),
            "open_task_count": SupportTask.objects.filter(
                customer=customer, status__in=OPEN_TASK_STATUSES
            ).count(),
            "note_count": InternalNote.objects.filter(customer=customer).count(),
            "lead_count": Lead.objects.filter(customer=customer).count(),
            "last_order_number": last_order.order_number if last_order else None,
            "last_order_status": last_order.status if last_order else None,
            "last_completed_order_number": last_completed.order_number if last_completed else None,
            "last_payment_status": getattr(getattr(last_order, "payment", None), "status", None),
        },
        "recent_orders": [
            _serialize_order(order) for order in list(all_orders.order_by("-created_at")[:5])
        ],
        "open_tasks": [
            {
                "task_id": str(task.id),
                "title": task.title,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "order_number": task.order.order_number if task.order else None,
                "assigned_to": task.assigned_to.email if task.assigned_to else None,
            }
            for task in open_tasks
        ],
        "recent_notes": [
            {
                "note_id": str(note.id),
                "note_type": note.note_type,
                "content": note.content,
                "order_number": note.order.order_number if note.order else None,
                "created_at": note.created_at.isoformat(),
            }
            for note in recent_notes
        ],
        "recent_leads": [
            {
                "lead_id": str(lead.id),
                "status": lead.status,
                "interest_summary": lead.interest_summary,
                "estimated_order_value": str(lead.estimated_order_value)
                if lead.estimated_order_value is not None
                else None,
            }
            for lead in recent_leads
        ],
    }


def get_customer_orders_summary(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Return a concise order summary for one customer."""
    customer = _resolve_target_customer(payload, context=context)
    if customer is None:
        return {"found": False, "error": "customer_not_found"}
    if not context.is_staff and str(customer.id) != str(context.user_id):
        return {"found": False, "error": "staff_required"}

    orders = Order.objects.filter(user=customer).select_related("payment").prefetch_related("items")
    completed_orders = orders.filter(status__in=COMPLETED_ORDER_STATUSES)
    status_counts = {
        row["status"]: row["count"]
        for row in orders.values("status").annotate(count=Count("id")).order_by()
    }
    return {
        "found": True,
        "customer_email": customer.email,
        "customer_name": customer.full_name,
        "order_count": orders.count(),
        "completed_order_count": completed_orders.count(),
        "total_revenue": str(completed_orders.aggregate(total=Sum("total")).get("total") or 0),
        "status_breakdown": status_counts,
        "recent_orders": [
            _serialize_order(order) for order in list(orders.order_by("-created_at")[:5])
        ],
    }


def search_internal_notes(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search internal notes by customer, order, conversation, or text."""
    if not context.is_staff:
        return {"results": [], "error": "staff_required"}

    queryset = InternalNote.objects.select_related(
        "order", "customer", "conversation", "created_by"
    )
    query = str(payload.get("query") or "").strip()
    order_number = str(payload.get("order_number") or "").strip()
    customer_email = str(payload.get("customer_email") or "").strip().lower()
    note_type = str(payload.get("note_type") or "").strip().lower()
    conversation_id = str(payload.get("conversation_id") or "").strip()
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)

    if query:
        queryset = queryset.filter(content__icontains=query)
    if order_number:
        queryset = queryset.filter(order__order_number__iexact=order_number)
    if customer_email:
        queryset = queryset.filter(customer__email__iexact=customer_email)
    if note_type:
        queryset = queryset.filter(note_type=note_type)
    if conversation_id:
        queryset = queryset.filter(conversation_id=conversation_id)

    notes = list(queryset.order_by("-created_at")[:limit])
    return {
        "results": [
            {
                "note_id": str(note.id),
                "note_type": note.note_type,
                "content": note.content,
                "order_number": note.order.order_number if note.order else None,
                "customer_email": note.customer.email if note.customer else None,
                "conversation_id": str(note.conversation_id) if note.conversation_id else None,
                "created_by": note.created_by.email if note.created_by else None,
                "created_at": note.created_at.isoformat(),
            }
            for note in notes
        ]
    }


def create_ticket_and_assign(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create a ticket-style support task with explicit ownership."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    summary = str(payload.get("summary") or "").strip()
    if not summary:
        return {"created": False, "error": "missing_summary"}

    ticket_type = (
        str(payload.get("ticket_type") or SupportTask.TaskType.SUPPORT_FOLLOW_UP).strip().lower()
    )
    task_type = _coerce_task_type(ticket_type)
    title = str(payload.get("title") or "").strip() or summary[:120]
    result = create_support_task(
        {
            "title": title,
            "description": summary,
            "task_type": task_type,
            "priority": payload.get("priority") or SupportTask.Priority.MEDIUM,
            "order_number": payload.get("order_number"),
            "conversation_id": payload.get("conversation_id"),
            "customer_email": payload.get("customer_email"),
            "assigned_to_email": payload.get("assigned_to_email"),
            "due_at": payload.get("due_at"),
            "due_in_days": payload.get("due_in_days"),
        },
        context,
    )
    if not result.get("created"):
        return result
    return {
        "created": True,
        "ticket_id": result["task_id"],
        "title": result["title"],
        "status": result["status"],
        "priority": result["priority"],
        "assigned_to": result["assigned_to"],
        "task_type": result["task_type"],
    }


def escalate_conversation_to_human(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Escalate a conversation and create a human follow-up task."""
    if not context.is_staff:
        return {"escalated": False, "error": "staff_required"}

    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    if conversation is None:
        return {"escalated": False, "error": "conversation_not_found"}

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        return {"escalated": False, "error": "missing_reason"}

    task_result = create_support_task(
        {
            "title": str(payload.get("title") or f"Escalacion humana · {conversation.id}")[:200],
            "description": reason,
            "task_type": SupportTask.TaskType.CONVERSATION_ESCALATION,
            "priority": payload.get("priority") or SupportTask.Priority.HIGH,
            "conversation_id": str(conversation.id),
            "customer_email": conversation.customer.email
            if conversation.customer
            else payload.get("customer_email"),
            "assigned_to_email": payload.get("assigned_to_email"),
            "due_in_days": payload.get("due_in_days") or 1,
        },
        context,
    )
    if not task_result.get("created"):
        return {"escalated": False, **task_result}

    conversation.status = Conversation.Status.ESCALATED
    conversation.summary = _append_text_block(conversation.summary, f"[Escalated] {reason}")
    conversation.metadata = {
        **conversation.metadata,
        "escalated_at": timezone.now().isoformat(),
        "escalated_by_user_id": context.user_id,
        "escalation_task_id": task_result["task_id"],
        "escalation_reason": reason,
    }
    conversation.save(update_fields=["status", "summary", "metadata", "updated_at"])

    note_result = create_internal_note(
        {
            "note_type": InternalNote.NoteType.SUPPORT,
            "conversation_id": str(conversation.id),
            "customer_email": conversation.customer.email
            if conversation.customer
            else payload.get("customer_email"),
            "content": f"Conversation escalated to human team. Reason: {reason}",
        },
        context,
    )
    return {
        "escalated": True,
        "conversation_id": str(conversation.id),
        "status": conversation.status,
        "task_id": task_result["task_id"],
        "note_id": note_result.get("note_id"),
    }


def generate_shipping_update(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Generate a customer-facing shipping update without sending it."""
    order = _resolve_order_for_context(payload.get("order_number"), context=context)
    if order is None:
        return {"generated": False, "error": "order_not_found"}

    carrier = _detect_carrier(order.tracking_number)
    status_label = order.get_status_display()
    delivery_hint = (
        f"Entrega estimada: {order.estimated_delivery.isoformat()}."
        if order.estimated_delivery
        else "Todavia no hay fecha estimada confirmada."
    )
    tracking_hint = (
        f"Tracking {order.tracking_number} por {carrier}."
        if order.tracking_number
        else "Todavia no hay tracking disponible."
    )
    status_messages: dict[str, str] = {
        Order.Status.READY_TO_SHIP: "Tu pedido ya esta listo para despacho y saldra en breve.",
        Order.Status.SHIPPED: "Tu pedido ya fue despachado y se encuentra en camino.",
        Order.Status.DELIVERED: "Tu pedido figura como entregado.",
        Order.Status.PREPARING: "Tu pedido esta en preparacion.",
    }
    body = status_messages.get(
        str(order.status), f"Tu pedido hoy figura como {status_label.lower()}."
    )

    draft_text = (
        f"Hola {order.user.first_name or ''}, {body} {tracking_hint} {delivery_hint}".strip()
    )
    return {
        "generated": True,
        "order_number": order.order_number,
        "status": order.status,
        "status_label": status_label,
        "tracking_number": order.tracking_number or None,
        "carrier": carrier,
        "estimated_delivery": order.estimated_delivery.isoformat()
        if order.estimated_delivery
        else None,
        "recommended_channel": "whatsapp" if order.user.phone else "email",
        "draft_text": draft_text,
    }


def create_payment_followup(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create a payment-review task and note from a detected issue."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    diagnosis = check_payment_issue(payload, context)
    if not diagnosis.get("found"):
        return {"created": False, **diagnosis}

    order_number = diagnosis["order_number"]
    priority = (
        SupportTask.Priority.HIGH
        if diagnosis["diagnosis"] in {"payment_rejected", "payment_approved_order_not_advanced"}
        else SupportTask.Priority.MEDIUM
    )
    summary = str(payload.get("summary") or diagnosis["recommended_action"]).strip()
    task_result = create_support_task(
        {
            "title": f"Seguimiento de pago · {order_number}",
            "description": summary,
            "task_type": SupportTask.TaskType.PAYMENT_REVIEW,
            "priority": priority,
            "order_number": order_number,
            "customer_email": payload.get("customer_email"),
            "assigned_to_email": payload.get("assigned_to_email"),
            "due_in_days": payload.get("due_in_days") or 1,
        },
        context,
    )
    if not task_result.get("created"):
        return task_result

    note_result = create_internal_note(
        {
            "note_type": InternalNote.NoteType.PAYMENT,
            "order_number": order_number,
            "customer_email": payload.get("customer_email"),
            "content": f"Payment follow-up created. Diagnosis: {diagnosis['diagnosis']}. {summary}",
        },
        context,
    )
    return {
        "created": True,
        "task_id": task_result["task_id"],
        "note_id": note_result.get("note_id"),
        "diagnosis": diagnosis["diagnosis"],
        "recommended_action": diagnosis["recommended_action"],
    }


def reserve_stock(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Reserve stock by decrementing available inventory and persisting an audit record."""
    if not context.is_staff:
        return {"reserved": False, "error": "staff_required"}

    wine = _resolve_wine(payload)
    if wine is None:
        return {"reserved": False, "error": "wine_not_found"}

    quantity = _parse_positive_int(payload.get("quantity"))
    if quantity is None:
        return {"reserved": False, "error": "invalid_quantity"}
    if wine.stock < quantity:
        return {"reserved": False, "error": "insufficient_stock", "available_stock": wine.stock}

    order = _resolve_order(payload.get("order_number"))
    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    customer = _resolve_customer(payload.get("customer_email"), conversation=conversation) or (
        order.user if order else None
    )
    wine.stock -= quantity
    wine.save(update_fields=["stock", "updated_at"])

    reservation = StockReservation.objects.create(
        wine=wine,
        quantity=quantity,
        order=order,
        conversation=conversation,
        customer=customer,
        created_by=_actor_from_context(context),
        status=StockReservation.Status.ACTIVE,
        reason=str(payload.get("reason") or "").strip(),
        metadata={"source": "ai_tool", "run_id": str(context.run.id)},
    )
    create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER if order else InternalNote.NoteType.GENERAL,
            "order_number": order.order_number if order else None,
            "conversation_id": str(conversation.id) if conversation else None,
            "customer_email": customer.email if customer else None,
            "content": f"Stock reservado: {quantity} unidad(es) de {wine.name} ({wine.sku}).",
        },
        context,
    )
    return {
        "reserved": True,
        "reservation_id": str(reservation.id),
        "sku": wine.sku,
        "wine_name": wine.name,
        "quantity": quantity,
        "remaining_stock": wine.stock,
        "order_number": order.order_number if order else None,
    }


def release_stock_reservation(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Release a full or partial stock reservation."""
    if not context.is_staff:
        return {"released": False, "error": "staff_required"}

    reservation = _resolve_stock_reservation(payload.get("reservation_id"))
    if reservation is None:
        return {"released": False, "error": "reservation_not_found"}
    if reservation.status not in {
        StockReservation.Status.ACTIVE,
        StockReservation.Status.PARTIALLY_RELEASED,
    }:
        return {"released": False, "error": "reservation_not_active"}

    remaining_quantity = reservation.quantity - reservation.released_quantity
    release_quantity = _parse_positive_int(payload.get("quantity")) or remaining_quantity
    if release_quantity > remaining_quantity:
        return {
            "released": False,
            "error": "invalid_quantity",
            "remaining_quantity": remaining_quantity,
        }

    reservation.wine.stock += release_quantity
    reservation.wine.save(update_fields=["stock", "updated_at"])
    reservation.released_quantity += release_quantity
    reservation.released_at = timezone.now()
    reservation.status = (
        StockReservation.Status.RELEASED
        if reservation.released_quantity >= reservation.quantity
        else StockReservation.Status.PARTIALLY_RELEASED
    )
    reservation.save(update_fields=["released_quantity", "released_at", "status", "updated_at"])

    create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER
            if reservation.order
            else InternalNote.NoteType.GENERAL,
            "order_number": reservation.order.order_number if reservation.order else None,
            "conversation_id": str(reservation.conversation_id)
            if reservation.conversation_id
            else None,
            "customer_email": reservation.customer.email if reservation.customer else None,
            "content": (
                f"Se liberaron {release_quantity} unidad(es) de la reserva {reservation.id} "
                f"para {reservation.wine.name} ({reservation.wine.sku})."
            ),
        },
        context,
    )
    return {
        "released": True,
        "reservation_id": str(reservation.id),
        "released_quantity": release_quantity,
        "remaining_reserved_quantity": reservation.quantity - reservation.released_quantity,
        "reservation_status": reservation.status,
        "current_stock": reservation.wine.stock,
    }


def create_restock_task(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create a restock task for a low-stock wine."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    wine = _resolve_wine(payload)
    if wine is None and payload.get("auto_low_stock", True):
        wine = (
            Wine.objects.filter(is_active=True, stock__lte=F("low_stock_threshold"))
            .order_by("stock", "name")
            .first()
        )
    if wine is None:
        return {"created": False, "error": "wine_not_found"}

    suggested_quantity = _parse_positive_int(payload.get("suggested_quantity")) or max(
        wine.low_stock_threshold * 2 - wine.stock, 1
    )
    result = create_support_task(
        {
            "title": f"Reponer stock · {wine.name}",
            "description": (
                f"SKU {wine.sku}. Stock actual: {wine.stock}. "
                f"Umbral: {wine.low_stock_threshold}. Reposicion sugerida: {suggested_quantity}."
            ),
            "task_type": SupportTask.TaskType.RESTOCK,
            "priority": payload.get("priority") or SupportTask.Priority.HIGH,
            "assigned_to_email": payload.get("assigned_to_email"),
            "due_in_days": payload.get("due_in_days") or 2,
        },
        context,
    )
    if not result.get("created"):
        return result
    return {
        "created": True,
        "task_id": result["task_id"],
        "sku": wine.sku,
        "wine_name": wine.name,
        "current_stock": wine.stock,
        "suggested_quantity": suggested_quantity,
    }


def sync_tracking_status(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return the best available tracking snapshot for an order."""
    order = _resolve_order_for_context(payload.get("order_number"), context=context)
    if order is None:
        return {"synced": False, "error": "order_not_found"}
    if not order.tracking_number:
        return {"synced": False, "error": "missing_tracking_number"}

    return {
        "synced": True,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "carrier": _detect_carrier(order.tracking_number),
        "integration_status": "not_configured",
        "tracking_status": _derive_tracking_status(order),
        "order_status": order.status,
        "estimated_delivery": order.estimated_delivery.isoformat()
        if order.estimated_delivery
        else None,
        "synced_at": timezone.now().isoformat(),
    }


def create_shipping_claim(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Create a shipping claim task and note for a delayed or problematic order."""
    if not context.is_staff:
        return {"created": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    if order is None:
        return {"created": False, "error": "order_not_found"}

    claim_reason = str(payload.get("claim_reason") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    if not claim_reason or not summary:
        return {"created": False, "error": "missing_summary"}

    task_result = create_support_task(
        {
            "title": f"Reclamo logistico · {order.order_number}",
            "description": f"{claim_reason}: {summary}",
            "task_type": SupportTask.TaskType.SHIPPING_CLAIM,
            "priority": payload.get("priority") or SupportTask.Priority.URGENT,
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "assigned_to_email": payload.get("assigned_to_email"),
            "due_in_days": payload.get("due_in_days") or 1,
        },
        context,
    )
    if not task_result.get("created"):
        return task_result

    note_result = create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER,
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "content": f"Reclamo logistico creado. Motivo: {claim_reason}. Detalle: {summary}",
        },
        context,
    )
    return {
        "created": True,
        "task_id": task_result["task_id"],
        "note_id": note_result.get("note_id"),
        "order_number": order.order_number,
    }


def request_order_cancellation(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Cancel an order after a human approval gate has executed the tool."""
    if not context.is_staff:
        return {"cancelled": False, "error": "staff_required"}

    order = _resolve_order(payload.get("order_number"))
    if order is None:
        return {"cancelled": False, "error": "order_not_found"}

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        return {"cancelled": False, "error": "missing_reason"}
    if not can_transition(order.status, Order.Status.CANCELLED):
        return {"cancelled": False, "error": "invalid_transition", "current_status": order.status}

    previous_status = order.status
    order.status = Order.Status.CANCELLED
    order.notes = _append_text_block(order.notes, f"[AI] Cancelacion aprobada. Motivo: {reason}")
    order.save(update_fields=["status", "notes", "updated_at"])

    note_result = create_internal_note(
        {
            "note_type": InternalNote.NoteType.ORDER,
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "content": f"Pedido cancelado tras aprobacion humana. Motivo: {reason}",
        },
        context,
    )
    payment_followup_task_id = None
    payment = _resolve_payment({"order_number": order.order_number}, context=context)
    if payment is not None and payment.status == Payment.Status.APPROVED:
        followup = create_support_task(
            {
                "title": f"Revisar devolucion o reembolso · {order.order_number}",
                "description": (
                    "El pedido fue cancelado luego de un pago aprobado. "
                    "Revisar la gestion financiera correspondiente."
                ),
                "task_type": SupportTask.TaskType.PAYMENT_REVIEW,
                "priority": SupportTask.Priority.HIGH,
                "order_number": order.order_number,
                "customer_email": order.user.email,
                "due_in_days": 1,
            },
            context,
        )
        payment_followup_task_id = followup.get("task_id")

    return {
        "cancelled": True,
        "order_number": order.order_number,
        "previous_status": previous_status,
        "status": order.status,
        "note_id": note_result.get("note_id"),
        "payment_followup_task_id": payment_followup_task_id,
    }


def _resolve_target_customer(payload: dict[str, object], *, context: ToolContext):
    conversation = _resolve_conversation(payload.get("conversation_id"), context=context)
    customer = _resolve_customer(payload.get("customer_email"), conversation=conversation)
    if customer is not None:
        return customer
    order = _resolve_order(payload.get("order_number"))
    if order is not None:
        return order.user
    if not context.is_staff and context.user_id:
        return _actor_from_context(context)
    return conversation.customer if conversation and conversation.customer_id else None


def _resolve_order_for_context(order_number: object, *, context: ToolContext) -> Order | None:
    order = _resolve_order(order_number)
    if order is None:
        return None
    if context.is_staff:
        return order
    if context.user_id and str(order.user_id) == str(context.user_id):
        return order
    return None


def _resolve_wine(payload: dict[str, object]) -> Wine | None:
    sku = str(payload.get("sku") or "").strip()
    slug = str(payload.get("slug") or "").strip()
    if sku:
        return Wine.objects.filter(sku__iexact=sku).first()
    if slug:
        return Wine.objects.filter(slug__iexact=slug).first()
    return None


def _resolve_stock_reservation(reservation_id: object) -> StockReservation | None:
    normalized = str(reservation_id or "").strip()
    if not normalized:
        return None
    return (
        StockReservation.objects.select_related("wine", "order", "customer", "conversation")
        .filter(id=normalized)
        .first()
    )


def _parse_positive_int(value: object) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _resolve_date_range(payload: dict[str, object]) -> tuple[date | None, date | None]:
    start_date = _parse_date(payload.get("start_date"))
    end_date = _parse_date(payload.get("end_date"))
    preset = str(payload.get("period") or "").strip().lower()
    if start_date or end_date or not preset:
        return start_date, end_date
    local_today = timezone.localdate()
    if preset == "last_7_days":
        return local_today - timedelta(days=6), local_today
    if preset == "current_month":
        return local_today.replace(day=1), local_today
    if preset == "previous_month":
        current_month_start = local_today.replace(day=1)
        last_day_previous_month = current_month_start - timedelta(days=1)
        return last_day_previous_month.replace(day=1), last_day_previous_month
    return local_today - timedelta(days=29), local_today


def _normalize_status_filters(payload: dict[str, object]) -> list[str]:
    raw_statuses = payload.get("statuses")
    if raw_statuses in (None, ""):
        raw_statuses = payload.get("status")
    statuses = _normalize_string_list(raw_statuses)
    allowed = {choice for choice, _ in Order.Status.choices}
    return [status for status in statuses if status in allowed]


def _coerce_task_type(ticket_type: str) -> str:
    allowed = {choice for choice, _ in SupportTask.TaskType.choices}
    return ticket_type if ticket_type in allowed else SupportTask.TaskType.SUPPORT_FOLLOW_UP


def _serialize_order(order: Order) -> dict[str, object]:
    customer_name = order.user.full_name or order.user.email
    payment = getattr(order, "payment", None)
    return {
        "order_number": order.order_number,
        "status": order.status,
        "status_label": order.get_status_display(),
        "payment_status": payment.status if payment else None,
        "shipping_method": order.shipping_method,
        "tracking_number": order.tracking_number or None,
        "estimated_delivery": order.estimated_delivery.isoformat()
        if order.estimated_delivery
        else None,
        "total": str(order.total),
        "customer_name": customer_name,
        "customer_email": order.user.email,
        "customer_phone": order.user.phone,
        "created_at": order.created_at.isoformat(),
        "item_count": sum(item.quantity for item in order.items.all()),
    }


def _detect_carrier(tracking_number: str) -> str:
    normalized = tracking_number.strip().upper()
    if normalized.startswith("AND"):
        return "Andreani"
    if normalized.startswith("OCA"):
        return "OCA"
    if normalized.startswith("COR"):
        return "Correo Argentino"
    return "Carrier externo"


def _derive_tracking_status(order: Order) -> str:
    mapping: dict[str, str] = {
        Order.Status.READY_TO_SHIP: "label_created",
        Order.Status.SHIPPED: "in_transit",
        Order.Status.DELIVERED: "delivered",
        Order.Status.CANCELLED: "cancelled",
        Order.Status.REFUNDED: "returned_or_refunded",
    }
    return mapping.get(str(order.status), str(order.status))


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if value in (None, ""):
        parsed = default
    else:
        try:
            parsed = int(str(value))
        except ValueError:
            parsed = default
    return max(minimum, min(parsed, maximum))
