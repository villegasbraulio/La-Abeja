"""Tests for transactional email fallbacks."""

from __future__ import annotations

from unittest.mock import patch

from apps.notifications.email import EmailService


def test_send_transactional_swallow_smtp_errors(settings) -> None:
    """Email failures should be logged without breaking the caller flow."""
    settings.DEFAULT_FROM_EMAIL = "ventas@laabeja.test"

    with patch(
        "apps.notifications.email.send_mail",
        side_effect=ConnectionRefusedError("[Errno 61] Connection refused"),
    ) as mocked_send_mail:
        sent = EmailService.send_transactional(
            to="cliente@example.com",
            template="order_confirmation",
            context={"order_number": "000123"},
        )

    assert sent is False
    mocked_send_mail.assert_called_once()
