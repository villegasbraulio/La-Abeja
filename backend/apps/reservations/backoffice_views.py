"""Views for the reservations backoffice API."""

from __future__ import annotations

import structlog
from django.db.models import Count, QuerySet
from rest_framework import filters, generics, permissions
from rest_framework.request import Request

from apps.authentication.permissions import IsStaffUser

from .backoffice_serializers import (
    BackofficeBookingSerializer,
    BackofficeExperienceSerializer,
    BackofficeTimeSlotSerializer,
)
from .models import Booking, Experience, TimeSlot

logger = structlog.get_logger(__name__)


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
