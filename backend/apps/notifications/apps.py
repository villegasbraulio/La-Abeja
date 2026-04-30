"""Notifications app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Configure notifications app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
