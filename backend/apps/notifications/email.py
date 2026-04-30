"""Transactional email wrapper."""

from __future__ import annotations

import structlog
from django.conf import settings
from django.core.mail import send_mail

logger = structlog.get_logger(__name__)


class EmailService:
    """Simple email service abstraction for transactional notifications."""

    @staticmethod
    def send_transactional(
        to: str | list[str],
        template: str,
        context: dict[str, object],
    ) -> None:
        """Send a lightweight email payload using Django's email backend."""
        recipients = [to] if isinstance(to, str) else to
        subject = f"Bodega La Abeja · {template.replace('_', ' ').title()}"
        body = "\n".join(f"{key}: {value}" for key, value in context.items())
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info("email_sent", template=template, recipients=recipients)
