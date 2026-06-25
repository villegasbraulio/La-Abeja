"""Public routes for winery visit reservations."""

from __future__ import annotations

from django.urls import path

from .views import (
    BookingCancelView,
    BookingDetailView,
    BookingListCreateView,
    BookingPaymentWebhookView,
    ExperienceListView,
    TimeSlotListView,
)

app_name = "reservations"

urlpatterns = [
    path("experiences/", ExperienceListView.as_view(), name="experience-list"),
    path("slots/", TimeSlotListView.as_view(), name="slot-list"),
    path("bookings/", BookingListCreateView.as_view(), name="booking-list"),
    path("bookings/<uuid:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path("bookings/<uuid:pk>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("payments/webhook/", BookingPaymentWebhookView.as_view(), name="booking-payment-webhook"),
]
