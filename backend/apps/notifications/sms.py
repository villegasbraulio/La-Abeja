"""SMS wrapper."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class SMSService:
    """Stub SMS service for local development and tests."""

    @staticmethod
    def send_message(to: str, body: str) -> None:
        """Log outbound SMS payloads."""
        logger.info("sms_sent", to=to, body=body)
