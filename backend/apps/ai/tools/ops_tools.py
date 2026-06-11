"""Operations-focused tools."""

from __future__ import annotations

from django.db.models import F

from apps.catalog.models import Wine
from apps.orders.models import Order

from .base import ToolContext


def list_low_stock_items(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return wines whose stock is at or below the threshold."""
    if not context.is_staff:
        return {"error": "staff_required", "results": []}
    limit = _payload_limit(payload, default=5)
    wines = Wine.objects.filter(is_active=True, stock__lte=F("low_stock_threshold")).order_by(
        "stock", "name"
    )[:limit]
    return {
        "results": [
            {
                "id": str(wine.id),
                "name": wine.name,
                "sku": wine.sku,
                "stock": wine.stock,
                "low_stock_threshold": wine.low_stock_threshold,
            }
            for wine in wines
        ]
    }


def list_pending_orders(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return the newest pending operational orders."""
    if not context.is_staff:
        return {"error": "staff_required", "results": []}
    limit = _payload_limit(payload, default=5)
    orders = (
        Order.objects.select_related("user")
        .filter(status__in=[Order.Status.PENDING_PAYMENT, Order.Status.PREPARING])
        .order_by("-created_at")[:limit]
    )
    return {
        "results": [
            {
                "id": str(order.id),
                "order_number": order.order_number,
                "customer_name": order.user.full_name,
                "status": order.status,
                "status_label": order.get_status_display(),
                "total": str(order.total),
            }
            for order in orders
        ]
    }


def _payload_limit(payload: dict[str, object], *, default: int) -> int:
    raw_limit = payload.get("limit")
    if raw_limit in (None, ""):
        return default
    try:
        return int(str(raw_limit))
    except ValueError:
        return default
