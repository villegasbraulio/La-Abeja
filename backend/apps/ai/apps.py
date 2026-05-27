"""AI app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class AIConfig(AppConfig):
    """Configure the AI support and operations app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    label = "ai"
