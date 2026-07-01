"""Views for the reservations backoffice API."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import structlog
from django.db.models import Count, F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from django.utils import timezone
from rest_framework import filters, generics, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsStaffUser

from .backoffice_serializers import (
    BackofficeBookingSerializer,
    BackofficeExperienceSerializer,
    BackofficeTimeSlotSerializer,
)
from .models import Booking, BookingManualRefund, Experience, TimeSlot

logger = structlog.get_logger(__name__)


class BackofficeReservationMetricsView(APIView):
    """Return booking, occupancy, and hospitality indicators for the backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Aggregate reservation KPIs by visit date for the selected period."""
        period = str(request.query_params.get("period") or "last_30_days")
        window = _resolve_reservation_window(period)
        grain = "month" if period in {"current_year", "last_12_months"} else "day"
        bookings = Booking.objects.select_related("time_slot", "time_slot__experience").filter(
            time_slot__date__gte=window["start_date"],
            time_slot__date__lte=window["end_date"],
        )
        slots = TimeSlot.objects.select_related("experience").filter(
            date__gte=window["start_date"],
            date__lte=window["end_date"],
        )
        open_slots = slots.filter(is_blocked=False)
        revenue_statuses = [
            Booking.Status.CONFIRMED,
            Booking.Status.COMPLETED,
            Booking.Status.NO_SHOW,
        ]
        revenue_bookings = bookings.filter(status__in=revenue_statuses)

        booking_count = bookings.count()
        revenue_booking_count = revenue_bookings.count()
        paid_aggregate = revenue_bookings.aggregate(
            total_revenue=Coalesce(Sum("total_price"), Decimal("0.00")),
            total_guests=Coalesce(Sum("guest_count"), 0),
        )
        checked_in_count = bookings.filter(checked_in_at__isnull=False).count()
        completed_count = bookings.filter(status=Booking.Status.COMPLETED).count()
        no_show_count = bookings.filter(status=Booking.Status.NO_SHOW).count()
        cancelled_count = bookings.filter(status=Booking.Status.CANCELLED).count()
        pending_payment_count = bookings.filter(status=Booking.Status.PENDING_PAYMENT).count()
        payment_failed_count = bookings.filter(status=Booking.Status.PAYMENT_FAILED).count()

        slot_aggregate = open_slots.aggregate(
            slot_count=Count("id"),
            total_capacity=Coalesce(Sum("capacity"), 0),
            available_spots=Coalesce(Sum("spots_available"), 0),
        )
        total_capacity = int(slot_aggregate["total_capacity"] or 0)
        available_spots = int(slot_aggregate["available_spots"] or 0)
        booked_guests = max(total_capacity - available_spots, 0)

        response = {
            "summary": {
                "period": window["label"],
                "start_at": window["start_at"].isoformat(),
                "end_at": window["end_at"].isoformat(),
                "booking_count": booking_count,
                "revenue_booking_count": revenue_booking_count,
                "total_revenue": _format_decimal(paid_aggregate["total_revenue"]),
                "average_booking_value": _format_decimal(
                    (paid_aggregate["total_revenue"] / revenue_booking_count)
                    if revenue_booking_count
                    else Decimal("0.00")
                ),
                "total_guests": int(paid_aggregate["total_guests"] or 0),
                "average_group_size": round(
                    (int(paid_aggregate["total_guests"] or 0) / revenue_booking_count),
                    2,
                )
                if revenue_booking_count
                else 0,
                "checked_in_count": checked_in_count,
                "completed_count": completed_count,
                "cancelled_count": cancelled_count,
                "no_show_count": no_show_count,
                "pending_payment_count": pending_payment_count,
                "payment_failed_count": payment_failed_count,
                "conversion_rate": _safe_ratio(revenue_booking_count, booking_count),
                "cancellation_rate": _safe_ratio(cancelled_count, booking_count),
                "no_show_rate": _safe_ratio(no_show_count, completed_count + no_show_count),
                "check_in_rate": _safe_ratio(checked_in_count, revenue_booking_count),
                "average_lead_days": _average_lead_days(bookings),
            },
            "capacity": {
                "slot_count": int(slot_aggregate["slot_count"] or 0),
                "blocked_slot_count": slots.filter(is_blocked=True).count(),
                "total_capacity": total_capacity,
                "booked_guests": booked_guests,
                "available_spots": available_spots,
                "occupancy_rate": _safe_ratio(booked_guests, total_capacity),
            },
            "timeline": _reservation_timeline(bookings, grain, revenue_statuses),
            "by_experience": _reservation_by_experience(
                bookings=bookings,
                slots=open_slots,
                revenue_statuses=revenue_statuses,
            ),
            "status_breakdown": _reservation_status_breakdown(bookings),
            "operations": {
                "special_requests_count": bookings.exclude(special_requests="").count(),
                "dietary_restrictions_count": sum(
                    1
                    for restrictions in bookings.values_list("dietary_restrictions", flat=True)
                    if restrictions
                ),
                "pending_refunds_count": BookingManualRefund.objects.filter(
                    status=BookingManualRefund.Status.PENDING,
                    booking__time_slot__date__gte=window["start_date"],
                    booking__time_slot__date__lte=window["end_date"],
                ).count(),
                "pending_payment_count": pending_payment_count,
                "payment_failed_count": payment_failed_count,
            },
            "upcoming_slots": _upcoming_slots(),
        }
        return Response(response)


class BackofficeExperienceListCreateView(generics.ListCreateAPIView):
    """List and create visit experiences for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeExperienceSerializer
    queryset = Experience.objects.all().annotate(
        bookings_count=Count("slots__bookings", distinct=True),
        slots_count=Count("slots", distinct=True),
    )
    pagination_class = None
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["name", "duration_minutes", "price_per_person", "is_active"]
    ordering = ["-is_featured", "name"]
    search_fields = ["name", "slug", "description", "experience_type"]

    def create(self, request: Request, *args: object, **kwargs: object):
        """Create a visit experience and log failures explicitly."""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_experience_create_failed", error=str(exc))
            raise


class BackofficeExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a visit experience."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeExperienceSerializer
    queryset = Experience.objects.all().annotate(
        bookings_count=Count("slots__bookings", distinct=True),
        slots_count=Count("slots", distinct=True),
    )


class BackofficeTimeSlotListCreateView(generics.ListCreateAPIView):
    """List and create visit slots for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeTimeSlotSerializer
    queryset = TimeSlot.objects.select_related("experience").all()
    pagination_class = None
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["date", "start_time", "capacity", "spots_available"]
    ordering = ["-date", "start_time"]
    search_fields = ["experience__name", "guide_name", "block_reason", "date"]

    def get_queryset(self) -> QuerySet[TimeSlot]:
        """Filter slots by the selected experience if present."""
        queryset = super().get_queryset()
        experience_id = self.request.query_params.get("experience")
        if experience_id:
            queryset = queryset.filter(experience_id=experience_id)
        return queryset


class BackofficeTimeSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a visit slot."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeTimeSlotSerializer
    queryset = TimeSlot.objects.select_related("experience").all()


class BackofficeBookingListCreateView(generics.ListCreateAPIView):
    """List and create bookings for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeBookingSerializer
    queryset = Booking.objects.select_related(
        "user",
        "time_slot",
        "time_slot__experience",
        "payment",
    ).all()
    pagination_class = None
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["created_at", "guest_count", "total_price", "status"]
    ordering = ["-created_at"]
    search_fields = [
        "confirmation_code",
        "user__email",
        "user__first_name",
        "user__last_name",
        "time_slot__experience__name",
        "time_slot__experience__slug",
    ]

    def get_queryset(self) -> QuerySet[Booking]:
        """Filter bookings by status or experience when requested."""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        experience_id = self.request.query_params.get("experience")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if experience_id:
            queryset = queryset.filter(time_slot__experience_id=experience_id)
        return queryset


class BackofficeBookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a visit booking."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeBookingSerializer
    queryset = Booking.objects.select_related(
        "user",
        "time_slot",
        "time_slot__experience",
        "payment",
    ).all()


def _resolve_reservation_window(period: str) -> dict[str, object]:
    today = timezone.localdate()
    normalized = period.strip().lower()
    end_date = today
    if normalized == "last_7_days":
        start_date = today - timedelta(days=6)
    elif normalized == "current_month":
        start_date = today.replace(day=1)
    elif normalized == "previous_month":
        end_date = today.replace(day=1) - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif normalized == "current_year":
        start_date = today.replace(month=1, day=1)
    elif normalized == "last_12_months":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=29)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_at": timezone.make_aware(datetime.combine(start_date, time.min)),
        "end_at": timezone.make_aware(datetime.combine(end_date, time.max)),
        "label": f"{start_date.isoformat()}..{end_date.isoformat()}",
    }


def _format_decimal(value: object) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value or "0"))
    return format(decimal_value.normalize(), "f")


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _average_lead_days(bookings: QuerySet[Booking]) -> float:
    lead_days = [
        (booking.time_slot.date - timezone.localtime(booking.created_at).date()).days
        for booking in bookings
        if booking.created_at and booking.time_slot_id
    ]
    return round(sum(lead_days) / len(lead_days), 1) if lead_days else 0.0


def _reservation_timeline(
    bookings: QuerySet[Booking],
    grain: str,
    revenue_statuses: list[str],
) -> dict[str, object]:
    trunc = TruncMonth if grain == "month" else TruncDay
    rows = (
        bookings.annotate(period=trunc("time_slot__date"))
        .values("period")
        .annotate(
            booking_count=Count("id"),
            guest_count=Coalesce(Sum("guest_count"), 0),
            total_revenue=Coalesce(
                Sum("total_price", filter=Q(status__in=revenue_statuses)),
                Decimal("0.00"),
            ),
        )
        .order_by("period")
    )
    return {
        "grain": grain,
        "results": [
            {
                "period": _date_key(row["period"]),
                "booking_count": int(row["booking_count"] or 0),
                "guest_count": int(row["guest_count"] or 0),
                "total_revenue": _format_decimal(row["total_revenue"]),
            }
            for row in rows
        ],
    }


def _reservation_by_experience(
    *,
    bookings: QuerySet[Booking],
    slots: QuerySet[TimeSlot],
    revenue_statuses: list[str],
) -> dict[str, object]:
    experience_ids = slots.values_list("experience_id", flat=True).distinct()
    results = []
    for experience in Experience.objects.filter(id__in=experience_ids).order_by("name"):
        experience_slots = slots.filter(experience=experience)
        experience_bookings = bookings.filter(time_slot__experience=experience)
        paid_bookings = experience_bookings.filter(status__in=revenue_statuses)
        slot_totals = experience_slots.aggregate(
            slot_count=Count("id"),
            total_capacity=Coalesce(Sum("capacity"), 0),
            available_spots=Coalesce(Sum("spots_available"), 0),
        )
        revenue_totals = paid_bookings.aggregate(
            guest_count=Coalesce(Sum("guest_count"), 0),
            total_revenue=Coalesce(Sum("total_price"), Decimal("0.00")),
        )
        capacity = int(slot_totals["total_capacity"] or 0)
        available = int(slot_totals["available_spots"] or 0)
        booked = max(capacity - available, 0)
        results.append(
            {
                "experience_id": str(experience.id),
                "experience_name": experience.name,
                "slot_count": int(slot_totals["slot_count"] or 0),
                "booking_count": experience_bookings.count(),
                "guest_count": int(revenue_totals["guest_count"] or 0),
                "total_revenue": _format_decimal(revenue_totals["total_revenue"]),
                "total_capacity": capacity,
                "booked_guests": booked,
                "occupancy_rate": _safe_ratio(booked, capacity),
            }
        )
    return {
        "results": sorted(
            results,
            key=lambda row: Decimal(str(row["total_revenue"] or "0")),
            reverse=True,
        )
    }


def _reservation_status_breakdown(bookings: QuerySet[Booking]) -> dict[str, object]:
    results = []
    for status_value, status_label in Booking.Status.choices:
        status_bookings = bookings.filter(status=status_value)
        totals = status_bookings.aggregate(
            guest_count=Coalesce(Sum("guest_count"), 0),
            total_revenue=Coalesce(Sum("total_price"), Decimal("0.00")),
        )
        results.append(
            {
                "status": status_value,
                "label": status_label,
                "booking_count": status_bookings.count(),
                "guest_count": int(totals["guest_count"] or 0),
                "total_revenue": _format_decimal(totals["total_revenue"]),
            }
        )
    return {"results": results}


def _upcoming_slots() -> list[dict[str, object]]:
    today = timezone.localdate()
    rows = (
        TimeSlot.objects.select_related("experience")
        .filter(date__gte=today, date__lte=today + timedelta(days=14), is_blocked=False)
        .annotate(booked_guests=F("capacity") - F("spots_available"))
        .order_by("date", "start_time")[:8]
    )
    return [
        {
            "slot_id": slot.id,
            "experience_name": slot.experience.name,
            "date": slot.date.isoformat(),
            "start_time": slot.start_time.isoformat(timespec="minutes"),
            "capacity": slot.capacity,
            "booked_guests": int(slot.booked_guests),
            "spots_available": slot.spots_available,
            "occupancy_rate": _safe_ratio(int(slot.booked_guests), slot.capacity),
        }
        for slot in rows
    ]


def _date_key(raw_value: object) -> str:
    if isinstance(raw_value, datetime):
        return raw_value.date().isoformat()
    if isinstance(raw_value, date):
        return raw_value.isoformat()
    return str(raw_value or "")
