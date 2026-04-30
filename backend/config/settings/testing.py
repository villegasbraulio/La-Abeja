"""Testing settings."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
MIGRATION_MODULES = {
    "authentication": None,
    "catalog": None,
    "orders": None,
    "payments": None,
    "reservations": None,
    "automations": None,
    "notifications": None,
}
