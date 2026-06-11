"""Sales and operations analytics tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TypedDict

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from apps.ai.models import SupportTask
from apps.orders.models import Cart, Order, OrderItem
from apps.payments.models import Payment

from .base import ToolContext

VALID_SALES_STATUSES = [
    Order.Status.PAID,
    Order.Status.PREPARING,
    Order.Status.READY_TO_SHIP,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
]


@dataclass(slots=True)
class DateWindow:
    """Normalized date window for analytics queries."""

    start_at: datetime
    end_at: datetime
    label: str


class ChannelBucket(TypedDict):
    channel: str
    order_count: int
    total_revenue: Decimal


def get_sales_summary(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return aggregate order, revenue, and bottle metrics."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    orders = _completed_orders(window)
    order_aggregate = orders.aggregate(
        order_count=Count("id"),
        total_revenue=Coalesce(Sum("total"), Decimal("0.00")),
        average_order_value=Coalesce(Avg("total"), Decimal("0.00")),
    )
    bottle_aggregate = OrderItem.objects.filter(order__in=orders).aggregate(
        bottles_sold=Coalesce(Sum("quantity"), 0),
    )
    return {
        "period": window.label,
        "start_at": window.start_at.isoformat(),
        "end_at": window.end_at.isoformat(),
        "order_count": int(order_aggregate["order_count"] or 0),
        "total_revenue": _format_decimal(order_aggregate["total_revenue"]),
        "average_order_value": _format_decimal(order_aggregate["average_order_value"]),
        "bottles_sold": int(bottle_aggregate["bottles_sold"] or 0),
    }


def get_sales_over_period(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return sales metrics grouped by day, week, or month."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    grain = str(payload.get("grain") or "day").strip().lower()
    trunc = _trunc_for_grain(grain)
    if trunc is None:
        return {"error": "invalid_grain"}

    order_rows = (
        _completed_orders(window)
        .annotate(period=trunc("created_at"))
        .values("period")
        .annotate(
            order_count=Count("id"),
            total_revenue=Coalesce(Sum("total"), Decimal("0.00")),
        )
        .order_by("period")
    )
    bottle_rows = (
        OrderItem.objects.filter(order__in=_completed_orders(window))
        .annotate(period=trunc("order__created_at"))
        .values("period")
        .annotate(bottles_sold=Coalesce(Sum("quantity"), 0))
        .order_by("period")
    )

    merged: dict[str, dict[str, object]] = {}
    for row in order_rows:
        key = _period_key(row["period"])
        merged[key] = {
            "period": key,
            "order_count": int(row["order_count"] or 0),
            "total_revenue": _format_decimal(row["total_revenue"]),
            "bottles_sold": 0,
        }
    for row in bottle_rows:
        key = _period_key(row["period"])
        merged.setdefault(
            key,
            {
                "period": key,
                "order_count": 0,
                "total_revenue": _format_decimal(Decimal("0.00")),
                "bottles_sold": 0,
            },
        )
        merged[key]["bottles_sold"] = int(row["bottles_sold"] or 0)

    return {
        "period": window.label,
        "grain": grain,
        "results": [merged[key] for key in sorted(merged.keys())],
    }


def get_sales_by_varietal(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Aggregate sold bottles and revenue by varietal."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)
    rows = (
        OrderItem.objects.filter(order__in=_completed_orders(window))
        .values("wine__varietal__name")
        .annotate(
            bottles_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("subtotal"), Decimal("0.00")),
            order_count=Count("order", distinct=True),
        )
        .order_by("-bottles_sold", "-revenue")[:limit]
    )
    return {
        "period": window.label,
        "results": [
            {
                "varietal": row["wine__varietal__name"] or "Sin varietal",
                "bottles_sold": int(row["bottles_sold"] or 0),
                "revenue": _format_decimal(row["revenue"]),
                "order_count": int(row["order_count"] or 0),
            }
            for row in rows
        ],
    }


def get_sales_by_bottle(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Aggregate sold bottles and revenue by SKU / label."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)
    rows = (
        OrderItem.objects.filter(order__in=_completed_orders(window))
        .values("wine_sku", "wine_name")
        .annotate(
            bottles_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("subtotal"), Decimal("0.00")),
            order_count=Count("order", distinct=True),
        )
        .order_by("-bottles_sold", "-revenue")[:limit]
    )
    return {
        "period": window.label,
        "results": [
            {
                "sku": row["wine_sku"],
                "wine_name": row["wine_name"],
                "bottles_sold": int(row["bottles_sold"] or 0),
                "revenue": _format_decimal(row["revenue"]),
                "order_count": int(row["order_count"] or 0),
            }
            for row in rows
        ],
    }


def get_top_skus(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return the best-performing SKUs by units, revenue, or order count."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)
    sort_by = str(payload.get("sort_by") or "bottles_sold").strip().lower()
    valid_sort_fields = {"bottles_sold", "revenue", "order_count"}
    if sort_by not in valid_sort_fields:
        return {"error": "invalid_sort_by"}

    rows = (
        OrderItem.objects.filter(order__in=_completed_orders(window))
        .values("wine_sku", "wine_name")
        .annotate(
            bottles_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("subtotal"), Decimal("0.00")),
            order_count=Count("order", distinct=True),
        )
        .order_by(f"-{sort_by}", "-revenue")[:limit]
    )
    return {
        "period": window.label,
        "sort_by": sort_by,
        "results": [
            {
                "sku": row["wine_sku"],
                "wine_name": row["wine_name"],
                "bottles_sold": int(row["bottles_sold"] or 0),
                "revenue": _format_decimal(row["revenue"]),
                "order_count": int(row["order_count"] or 0),
            }
            for row in rows
        ],
    }


def get_repeat_customers_metrics(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Estimate repeat-customer behavior from completed orders."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    orders = _completed_orders(window)
    per_customer = list(
        orders.values("user_id", "user__email")
        .annotate(
            order_count=Count("id"),
            revenue=Coalesce(Sum("total"), Decimal("0.00")),
            last_order_at=Max("created_at"),
        )
        .order_by("-revenue")
    )
    unique_customers = len(per_customer)
    repeat_customers = [row for row in per_customer if int(row["order_count"] or 0) >= 2]
    total_revenue = sum(
        ((row["revenue"] or Decimal("0.00")) for row in per_customer), Decimal("0.00")
    )
    return {
        "period": window.label,
        "unique_customers": unique_customers,
        "repeat_customers": len(repeat_customers),
        "repeat_rate": round((len(repeat_customers) / unique_customers), 4)
        if unique_customers
        else 0.0,
        "average_revenue_per_customer": _format_decimal(
            (total_revenue / unique_customers) if unique_customers else Decimal("0.00")
        ),
        "top_repeat_customers": [
            {
                "customer_email": row["user__email"],
                "order_count": int(row["order_count"] or 0),
                "revenue": _format_decimal(row["revenue"]),
                "last_order_at": row["last_order_at"].isoformat() if row["last_order_at"] else None,
            }
            for row in repeat_customers[: min(5, len(repeat_customers))]
        ],
    }


def get_conversion_funnel(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Estimate a simple commerce funnel from carts, orders, and payments."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    carts = Cart.objects.filter(created_at__gte=window.start_at, created_at__lte=window.end_at)
    carts_with_items = carts.annotate(item_count=Count("items")).filter(item_count__gt=0)
    orders = Order.objects.filter(created_at__gte=window.start_at, created_at__lte=window.end_at)
    paid_orders = orders.filter(status__in=VALID_SALES_STATUSES)
    payments = Payment.objects.filter(
        created_at__gte=window.start_at, created_at__lte=window.end_at
    )
    rejected_payments = payments.filter(status=Payment.Status.REJECTED)

    cart_count = carts_with_items.count()
    order_count = orders.count()
    paid_order_count = paid_orders.count()
    return {
        "period": window.label,
        "cart_count": cart_count,
        "order_count": order_count,
        "paid_order_count": paid_order_count,
        "rejected_payment_count": rejected_payments.count(),
        "cart_to_order_rate": round(order_count / cart_count, 4) if cart_count else 0.0,
        "order_to_paid_rate": round(paid_order_count / order_count, 4) if order_count else 0.0,
        "cart_abandonment_rate": round((cart_count - order_count) / cart_count, 4)
        if cart_count
        else 0.0,
    }


def get_returns_and_incidents_metrics(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Summarize refunds, cancellations, payment failures, and AI-generated incidents."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    orders = Order.objects.filter(created_at__gte=window.start_at, created_at__lte=window.end_at)
    total_orders = orders.count()
    refunded_orders = orders.filter(status=Order.Status.REFUNDED).count()
    cancelled_orders = orders.filter(status=Order.Status.CANCELLED).count()
    payment_failed_orders = orders.filter(status=Order.Status.PAYMENT_FAILED).count()
    incident_task_count = SupportTask.objects.filter(
        created_at__gte=window.start_at,
        created_at__lte=window.end_at,
        task_type__in=[
            SupportTask.TaskType.ORDER_ISSUE,
            SupportTask.TaskType.ORDER_REVIEW,
            SupportTask.TaskType.SHIPPING_CLAIM,
            SupportTask.TaskType.CANCELLATION_REVIEW,
        ],
    ).count()
    return {
        "period": window.label,
        "total_orders": total_orders,
        "refunded_orders": refunded_orders,
        "cancelled_orders": cancelled_orders,
        "payment_failed_orders": payment_failed_orders,
        "incident_task_count": incident_task_count,
        "incident_rate": round((incident_task_count / total_orders), 4) if total_orders else 0.0,
    }


def get_sales_by_channel(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Aggregate completed orders by source channel when the order payload carries that tag."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    rows = (
        _completed_orders(window)
        .values("shipping_address")
        .annotate(order_count=Count("id"), total_revenue=Coalesce(Sum("total"), Decimal("0.00")))
    )
    grouped: dict[str, ChannelBucket] = {}
    for row in rows:
        shipping_address_raw = row.get("shipping_address") or {}
        shipping_address = shipping_address_raw if isinstance(shipping_address_raw, dict) else {}
        channel = (
            str(
                shipping_address.get("source_channel")
                or shipping_address.get("channel")
                or "unknown"
            )
            .strip()
            .lower()
        )
        bucket = grouped.setdefault(
            channel,
            {"channel": channel, "order_count": 0, "total_revenue": Decimal("0.00")},
        )
        bucket["order_count"] += int(row["order_count"] or 0)
        bucket["total_revenue"] += row["total_revenue"] or Decimal("0.00")

    return {
        "period": window.label,
        "results": [
            {
                "channel": channel,
                "order_count": value["order_count"],
                "total_revenue": _format_decimal(value["total_revenue"]),
            }
            for channel, value in sorted(
                grouped.items(), key=lambda item: item[1]["total_revenue"], reverse=True
            )
        ],
    }


def get_margin_estimate_by_product(
    payload: dict[str, object], context: ToolContext
) -> dict[str, object]:
    """Estimate margin contribution by SKU using current catalog cost_price."""
    if not context.is_staff:
        return {"error": "staff_required"}

    window = _resolve_date_window(payload)
    limit = _bounded_int(payload.get("limit"), default=10, minimum=1, maximum=25)
    rows = (
        OrderItem.objects.filter(order__in=_completed_orders(window))
        .annotate(
            estimated_cost_line=ExpressionWrapper(
                F("quantity") * F("wine__cost_price"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .values("wine__sku", "wine__name")
        .annotate(
            bottles_sold=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("subtotal"), Decimal("0.00")),
            estimated_cost=Coalesce(Sum("estimated_cost_line"), Decimal("0.00")),
        )
        .order_by("-revenue")[:limit]
    )
    return {
        "period": window.label,
        "results": [
            {
                "sku": row["wine__sku"],
                "wine_name": row["wine__name"],
                "bottles_sold": int(row["bottles_sold"] or 0),
                "revenue": _format_decimal(row["revenue"]),
                "estimated_cost": _format_decimal(row["estimated_cost"]),
                "estimated_margin": _format_decimal(
                    (row["revenue"] or Decimal("0.00"))
                    - (row["estimated_cost"] or Decimal("0.00"))
                ),
            }
            for row in rows
        ],
    }


def _resolve_date_window(payload: dict[str, object]) -> DateWindow:
    preset = str(payload.get("period") or "").strip().lower()
    end_date = _parse_date(payload.get("end_date")) or timezone.localdate()
    start_date = _parse_date(payload.get("start_date"))
    if start_date is None:
        if preset == "last_7_days":
            start_date = end_date - timedelta(days=6)
        elif preset == "current_month":
            start_date = end_date.replace(day=1)
        elif preset == "previous_month":
            first_day_current_month = end_date.replace(day=1)
            end_date = first_day_current_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
        else:
            start_date = end_date - timedelta(days=29)

    start_at = timezone.make_aware(datetime.combine(start_date, time.min))
    end_at = timezone.make_aware(datetime.combine(end_date, time.max))
    label = f"{start_date.isoformat()}..{end_date.isoformat()}"
    return DateWindow(start_at=start_at, end_at=end_at, label=label)


def _completed_orders(window: DateWindow):
    return Order.objects.filter(
        status__in=VALID_SALES_STATUSES,
        created_at__gte=window.start_at,
        created_at__lte=window.end_at,
    )


def _parse_date(raw_value: object) -> date | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _format_decimal(value: object) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value or "0"))
    return format(decimal_value.normalize(), "f")


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if value in (None, ""):
        parsed = default
    else:
        try:
            parsed = int(str(value))
        except ValueError:
            parsed = default
    return max(minimum, min(parsed, maximum))


def _trunc_for_grain(grain: str):
    mapping = {
        "day": TruncDay,
        "week": TruncWeek,
        "month": TruncMonth,
    }
    return mapping.get(grain)


def _period_key(raw_value: object) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, datetime):
        return raw_value.date().isoformat()
    return str(raw_value)
