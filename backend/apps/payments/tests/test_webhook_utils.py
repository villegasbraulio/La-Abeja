"""Coverage for Mercado Pago webhook signature helpers."""

from __future__ import annotations

import hashlib
import hmac

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.payments.webhook_utils import has_valid_signature


def _signed_request(*, secret: str, data_id: str = "99887766", request_id: str = "req-123"):
    ts_value = str(int(timezone.now().timestamp()))
    template = f"id:{data_id.lower()};request-id:{request_id};ts:{ts_value};"
    signature = hmac.new(
        secret.encode("utf-8"),
        template.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    factory = APIRequestFactory()
    request = factory.post(
        f"/api/v1/payments/webhook/?data.id={data_id}&type=payment",
        {"id": 12345, "type": "payment", "data": {"id": data_id}},
        format="json",
        HTTP_X_SIGNATURE=f"ts={ts_value},v1={signature}",
        HTTP_X_REQUEST_ID=request_id,
    )
    return Request(request)


def test_webhook_signature_accepts_valid_hmac(settings) -> None:
    """A valid Mercado Pago signature should be accepted."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = "top-secret"
    settings.MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = True

    request = _signed_request(secret="top-secret")

    assert has_valid_signature(request, {"type": "payment", "data": {"id": "99887766"}}) is True


def test_webhook_signature_rejects_missing_secret_when_required(settings) -> None:
    """Production-like settings should not accept unsigned callbacks."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = ""
    settings.MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = True
    request = _signed_request(secret="unused")

    assert has_valid_signature(request, {"type": "payment", "data": {"id": "99887766"}}) is False


def test_webhook_signature_allows_unsigned_callbacks_when_disabled(settings) -> None:
    """Local and test environments can keep webhook signatures optional."""
    settings.MERCADOPAGO_WEBHOOK_SECRET = ""
    settings.MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = False
    request = _signed_request(secret="unused")

    assert has_valid_signature(request, {"type": "payment", "data": {"id": "99887766"}}) is True
