"""Routes for the reservations backoffice API."""

from __future__ import annotations

from django.urls import path

from .backoffice_views import (
    BackofficeBookingDetailView,
    BackofficeBookingListCreateView,
    BackofficeExperienceDetailView,
    BackofficeExperienceListCreateView,
    BackofficeReservationMetricsView,
    BackofficeTimeSlotDetailView,
    BackofficeTimeSlotListCreateView,
)

app_name = "reservations_backoffice"

urlpatterns = [
    path(
        "visits/reservation-metrics/",
        BackofficeReservationMetricsView.as_view(),
        name="reservation-metrics",
    ),
    path(
        "visits/experiences/",
        BackofficeExperienceListCreateView.as_view(),
        name="experience-list",
    ),
    path(
        "visits/experiences/<uuid:pk>/",
        BackofficeExperienceDetailView.as_view(),
        name="experience-detail",
    ),
    path("visits/slots/", BackofficeTimeSlotListCreateView.as_view(), name="slot-list"),
    path("visits/slots/<int:pk>/", BackofficeTimeSlotDetailView.as_view(), name="slot-detail"),
    path("visits/bookings/", BackofficeBookingListCreateView.as_view(), name="booking-list"),
    path(
        "visits/bookings/<uuid:pk>/",
        BackofficeBookingDetailView.as_view(),
        name="booking-detail",
    ),
]
