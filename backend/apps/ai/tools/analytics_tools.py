"""Sales and operations analytics tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from apps.orders.models import Order, OrderItem

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
        "total_revenue": str(order_aggregate["total_revenue"] or Decimal("0.00")),
        "average_order_value": str(order_aggregate["average_order_value"] or Decimal("0.00")),
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
            "total_revenue": str(row["total_revenue"] or Decimal("0.00")),
            "bottles_sold": 0,
        }
    for row in bottle_rows:
        key = _period_key(row["period"])
        merged.setdefault(
            key,
            {"period": key, "order_count": 0, "total_revenue": str(Decimal("0.00")), "bottles_sold": 0},
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
    limit = max(1, min(int(payload.get("limit") or 10), 25))
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
                "revenue": str(row["revenue"] or Decimal("0.00")),
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
    limit = max(1, min(int(payload.get("limit") or 10), 25))
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
                "revenue": str(row["revenue"] or Decimal("0.00")),
                "order_count": int(row["order_count"] or 0),
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
