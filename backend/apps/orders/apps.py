"""Orders app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Configure orders app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"

    def ready(self) -> None:
        """Import signals after app registry setup."""
        from . import signals  # noqa: F401
