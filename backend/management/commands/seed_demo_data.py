"""Compatibility import for the canonical demo seed command."""

from apps.catalog.management.commands.seed_demo_data import Command

__all__ = ["Command"]
