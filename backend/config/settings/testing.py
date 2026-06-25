"""Testing settings."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
AI_ENABLE_PGVECTOR = False
MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = False
