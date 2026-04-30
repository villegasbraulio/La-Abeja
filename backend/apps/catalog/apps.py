"""Catalog app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Configure the wine catalog app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    label = "catalog"
