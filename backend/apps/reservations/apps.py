"""Reservations app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    """Configure reservations app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reservations"
    label = "reservations"
