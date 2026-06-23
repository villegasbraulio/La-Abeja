"""Shared helpers for Mercado Pago webhook validation."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.conf import settings
from rest_framework.request import Request


def parse_signature_header(signature_header: str) -> tuple[str | None, str | None]:
    """Split Mercado Pago's x-signature header into timestamp and digest."""
    ts_value: str | None = None
    v1_value: str | None = None
    for fragment in signature_header.split(","):
        key, _, value = fragment.partition("=")
        normalized_key = key.strip().lower()
        if normalized_key == "ts":
            ts_value = value.strip()
        if normalized_key == "v1":
            v1_value = value.strip()
    return ts_value, v1_value


def has_valid_signature(request: Request, payload: dict[str, Any]) -> bool:
    """Validate webhook origin when a secret key is configured."""
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        return True

    signature_header = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")
    data_id = request.query_params.get("data.id") or str((payload.get("data") or {}).get("id", ""))
    ts_value, received_signature = parse_signature_header(signature_header)

    if not data_id or not request_id or not ts_value or not received_signature:
        return False

    template = f"id:{data_id};request-id:{request_id};ts:{ts_value};"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        template.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)


def build_webhook_deduplication_key(
    *,
    topic: str,
    notification_id: str,
    payment_resource_id: str,
    payload: dict[str, Any],
) -> str:
    """Build a stable key for repeated deliveries of the same notification."""
    identity = f"{topic}:{notification_id}:{payment_resource_id}"
    if notification_id == "unknown" and not payment_resource_id:
        identity = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
