"""Tools for order support."""

from __future__ import annotations

from apps.orders.models import Order

from .base import ToolContext


def get_order_by_number(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Fetch a single order while respecting ownership rules."""
    order_number = str(payload.get("order_number") or "").strip()
    if not order_number:
        return {"found": False, "error": "missing_order_number"}
    if not context.is_staff and context.user_id is None:
        return {"found": False, "error": "authentication_required"}

    queryset = Order.objects.select_related("user")
    if not context.is_staff and context.user_id:
        queryset = queryset.filter(user_id=context.user_id)

    order = queryset.filter(order_number__iexact=order_number).first()
    if order is None:
        return {"found": False}

    payment = getattr(order, "payment", None)
    return {
        "found": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "status_label": order.get_status_display(),
        "payment_status": payment.status if payment else None,
        "shipping_method": order.shipping_method,
        "shipping_method_label": order.get_shipping_method_display(),
        "tracking_number": order.tracking_number,
        "estimated_delivery": str(order.estimated_delivery) if order.estimated_delivery else None,
        "total": str(order.total),
    }
