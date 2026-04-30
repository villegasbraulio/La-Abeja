"""Payments app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """Configure payments app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
