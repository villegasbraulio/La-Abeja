"""Development settings."""

from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = True
MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = os.getenv(
    "MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED",
    "False",
).lower() == "true"
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
