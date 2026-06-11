"""Minimal Mercado Pago client for Checkout Pro integration."""

from __future__ import annotations

import json
import uuid
from typing import Any, cast
from urllib import error, request

from django.conf import settings

from apps.orders.models import Order


class MercadoPagoAPIError(Exception):
    """Raised when Mercado Pago returns an error response."""


class MercadoPagoClient:
    """Small wrapper around Mercado Pago's HTTP API."""

    base_url = "https://api.mercadopago.com"

    def __init__(self, access_token: str | None = None) -> None:
        """Store credentials for outgoing API calls."""
        self.access_token = access_token or settings.MERCADOPAGO_ACCESS_TOKEN
        if not self.access_token:
            raise MercadoPagoAPIError("Mercado Pago no está configurado en este entorno.")

    def create_preference(self, order: Order) -> dict[str, Any]:
        """Create a Checkout Pro preference for a specific order."""
        payer_name, payer_surname = self._resolve_payer_name(order)
        shipping_snapshot = self._get_shipping_snapshot(order)
        payload = {
            "items": [
                {
                    "id": item.wine_sku,
                    "title": item.wine_name,
                    "description": f"Pedido {order.order_number}",
                    "currency_id": "ARS",
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                }
                for item in order.items.all()
            ],
            "payer": {
                "name": payer_name,
                "surname": payer_surname,
                "email": order.user.email,
            },
            "external_reference": str(order.id),
            "notification_url": f"{settings.BACKEND_URL}/api/v1/payments/webhook/",
            "back_urls": {
                "success": (
                    f"{settings.FRONTEND_URL}/checkout/resultado"
                    f"?order_id={order.id}&status=approved"
                ),
                "failure": (
                    f"{settings.FRONTEND_URL}/checkout/resultado"
                    f"?order_id={order.id}&status=failure"
                ),
                "pending": (
                    f"{settings.FRONTEND_URL}/checkout/resultado"
                    f"?order_id={order.id}&status=pending"
                ),
            },
            "auto_return": "approved",
            "shipments": {
                "cost": float(order.shipping_cost),
                "mode": "not_specified",
            },
            "metadata": {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "shipping_method": order.shipping_method,
                "shipping_provider": shipping_snapshot.get("provider", ""),
                "shipping_service_level": shipping_snapshot.get("service_level", ""),
                "shipping_city": str(order.shipping_address.get("city", "")),
                "shipping_province": str(order.shipping_address.get("province", "")),
            },
            "payment_methods": {
                "installments": 6,
            },
        }
        return self._request(
            method="POST",
            path="/checkout/preferences",
            body=payload,
            idempotency_key=str(uuid.uuid4()),
        )

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        """Fetch the latest payment status from Mercado Pago."""
        return self._request(method="GET", path=f"/v1/payments/{payment_id}")

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated request against Mercado Pago."""
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")

        http_request = request.Request(
            url=f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        if idempotency_key:
            http_request.add_header("X-Idempotency-Key", idempotency_key)

        try:
            with request.urlopen(http_request, timeout=15) as response:
                content = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise MercadoPagoAPIError(
                f"Mercado Pago devolvió HTTP {exc.code}: {details or exc.reason}"
            ) from exc
        except error.URLError as exc:
            raise MercadoPagoAPIError(
                "No pudimos comunicarnos con Mercado Pago."
            ) from exc

        try:
            return cast(dict[str, Any], json.loads(content))
        except json.JSONDecodeError as exc:
            raise MercadoPagoAPIError(
                "Mercado Pago devolvió una respuesta inválida."
            ) from exc

    def _resolve_payer_name(self, order: Order) -> tuple[str, str]:
        """Prefer customer account data and fall back to the shipping recipient."""
        first_name = (order.user.first_name or "").strip()
        last_name = (order.user.last_name or "").strip()
        if first_name or last_name:
            return first_name, last_name

        recipient_name = str(order.shipping_address.get("recipient_name", "")).strip()
        if not recipient_name:
            return "Cliente", "La Abeja"
        name_parts = recipient_name.split(maxsplit=1)
        if len(name_parts) == 1:
            return name_parts[0], ""
        return name_parts[0], name_parts[1]

    def _get_shipping_snapshot(self, order: Order) -> dict[str, Any]:
        """Return the quote metadata stored at checkout time when available."""
        snapshot = order.shipping_address.get("_shipping_quote")
        if isinstance(snapshot, dict):
            return snapshot
        return {}
