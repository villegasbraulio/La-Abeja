"""WhatsApp wrapper."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class WhatsAppService:
    """Stub WhatsApp service for local development and tests."""

    @staticmethod
    def send_template(to: str, template: str, params: list[str]) -> None:
        """Log outbound WhatsApp template payloads."""
        logger.info("whatsapp_sent", to=to, template=template, params=params)
