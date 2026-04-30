"""Authentication app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Configure the custom authentication app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    label = "authentication"

    def ready(self) -> None:
        """Import signals after the app registry is fully populated."""
        from . import signals  # noqa: F401
