"""Mercado Pago client backed by the official Python SDK."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlsplit

import structlog
from django.conf import settings

from apps.orders.access import build_guest_access_token
from apps.orders.models import Order
from apps.reservations.access import build_guest_access_token as build_booking_guest_access_token
from apps.reservations.models import Booking

try:
    import mercadopago
    from mercadopago.config import RequestOptions
except ImportError:  # pragma: no cover - handled at runtime when the SDK is missing
    mercadopago = None
    RequestOptions = None


class MercadoPagoAPIError(Exception):
    """Raised when Mercado Pago returns an error response."""


logger = structlog.get_logger(__name__)


class MercadoPagoClient:
    """Small wrapper around the official Mercado Pago SDK."""

    def __init__(self, access_token: str | None = None) -> None:
        """Store credentials and initialize the official SDK."""
        self.access_token = access_token or settings.MERCADOPAGO_ACCESS_TOKEN
        if not self.access_token:
            raise MercadoPagoAPIError("Mercado Pago no está configurado en este entorno.")
        if mercadopago is None:
            raise MercadoPagoAPIError(
                "El SDK oficial de Mercado Pago no está instalado en este entorno."
            )
        self.sdk = mercadopago.SDK(self.access_token)

    def create_preference(
        self,
        order: Order,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Checkout Pro preference for a specific order."""
        payer_name, payer_surname = self._resolve_payer_name(order)
        shipping_snapshot = self._get_shipping_snapshot(order)
        payload = {
            "items": self._build_preference_items(order),
            "payer": {
                "name": payer_name,
                "surname": payer_surname,
                "email": self._resolve_customer_email(order),
            },
            "external_reference": str(order.id),
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
        notification_url = self._build_notification_url()
        if notification_url:
            payload["notification_url"] = notification_url
        back_urls = self._build_back_urls(order)
        if back_urls:
            payload["back_urls"] = back_urls
            payload["auto_return"] = "approved"
        logger.info(
            "mercadopago_preference_urls_built",
            order_id=str(order.id),
            notification_url=notification_url,
            has_back_urls=bool(back_urls),
        )
        stable_key = idempotency_key or f"mercadopago:preference:{order.id}"
        request_options = RequestOptions(
            access_token=self.access_token,
            custom_headers={"x-idempotency-key": stable_key},
        )
        response = self.sdk.preference().create(payload, request_options)
        return self._unwrap_response(
            response,
            fallback_message="No pudimos crear la preferencia de pago en Mercado Pago.",
        )

    def create_booking_preference(
        self,
        booking: Booking,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Checkout Pro preference for a specific visit booking."""
        payer_name, payer_surname = self._resolve_booking_payer_name(booking)
        payload = {
            "items": self._build_booking_preference_items(booking),
            "payer": {
                "name": payer_name,
                "surname": payer_surname,
                "email": self._resolve_booking_customer_email(booking),
            },
            "external_reference": str(booking.id),
            "metadata": {
                "booking_id": str(booking.id),
                "confirmation_code": booking.confirmation_code,
                "experience_slug": booking.time_slot.experience.slug,
                "experience_name": booking.time_slot.experience.name,
                "slot_date": booking.time_slot.date.isoformat(),
                "slot_start_time": booking.time_slot.start_time.isoformat(),
                "hold_expires_at": booking.hold_expires_at.isoformat()
                if booking.hold_expires_at
                else "",
            },
            "payment_methods": {
                "installments": 6,
            },
        }
        if booking.hold_expires_at:
            payload["expires"] = True
            payload["expiration_date_from"] = booking.created_at.isoformat()
            payload["expiration_date_to"] = booking.hold_expires_at.isoformat()
        notification_url = self._build_booking_notification_url()
        if notification_url:
            payload["notification_url"] = notification_url
        back_urls = self._build_booking_back_urls(booking)
        if back_urls:
            payload["back_urls"] = back_urls
            payload["auto_return"] = "approved"
        logger.info(
            "mercadopago_booking_preference_urls_built",
            booking_id=str(booking.id),
            notification_url=notification_url,
            has_back_urls=bool(back_urls),
        )
        stable_key = idempotency_key or f"mercadopago:booking:{booking.id}"
        request_options = RequestOptions(
            access_token=self.access_token,
            custom_headers={"x-idempotency-key": stable_key},
        )
        response = self.sdk.preference().create(payload, request_options)
        return self._unwrap_response(
            response,
            fallback_message="No pudimos crear la preferencia de pago de la visita.",
        )

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        """Fetch the latest payment status from Mercado Pago."""
        response = self.sdk.payment().get(payment_id)
        return self._unwrap_response(
            response,
            fallback_message="No pudimos consultar el pago en Mercado Pago.",
        )

    def search_payments(self, *, external_reference: str) -> list[dict[str, Any]]:
        """Find payments when a webhook never supplied the payment ID."""
        response = self.sdk.payment().search(
            {
                "external_reference": external_reference,
                "sort": "date_created",
                "criteria": "desc",
                "limit": 20,
            }
        )
        body = self._unwrap_response(
            response,
            fallback_message="No pudimos reconciliar los pagos con Mercado Pago.",
        )
        results = body.get("results")
        if not isinstance(results, list):
            return []
        return [item for item in results if isinstance(item, dict)]

    def _resolve_payer_name(self, order: Order) -> tuple[str, str]:
        """Prefer customer account data and fall back to the shipping recipient."""
        first_name = (order.user.first_name or "").strip() if order.user_id else ""
        last_name = (order.user.last_name or "").strip() if order.user_id else ""
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

    def _build_preference_items(self, order: Order) -> list[dict[str, Any]]:
        """Return Mercado Pago items including shipping as a payable line item."""
        items = [
            {
                "id": item.wine_sku,
                "title": item.wine_name,
                "description": f"Pedido {order.order_number}",
                "currency_id": "ARS",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
            }
            for item in order.items.all()
        ]

        if order.shipping_cost > 0:
            items.append(
                {
                    "id": f"{order.order_number}-shipping",
                    "title": order.get_shipping_method_display(),
                    "description": f"Envío del pedido {order.order_number}",
                    "currency_id": "ARS",
                    "quantity": 1,
                    "unit_price": float(order.shipping_cost),
                }
            )

        return items

    def _resolve_customer_email(self, order: Order) -> str:
        """Return the order email for Mercado Pago payer data."""
        if order.customer_email:
            return order.customer_email
        if order.user_id and order.user:
            return order.user.email
        raise MercadoPagoAPIError("El pedido no tiene un email válido para cobrar.")

    def _resolve_booking_customer_email(self, booking: Booking) -> str:
        """Return the booking email for Mercado Pago payer data."""
        if booking.customer_email:
            return booking.customer_email
        if booking.user_id and booking.user:
            return booking.user.email
        raise MercadoPagoAPIError("La reserva no tiene un email válido para cobrar.")

    def _build_back_urls(self, order: Order) -> dict[str, str]:
        """Return public back URLs when the frontend host can receive redirects."""
        frontend_url = self._resolve_public_base_url(
            settings.FRONTEND_URL,
            setting_name="FRONTEND_URL",
        )
        if not frontend_url:
            return {}

        guest_access_token = build_guest_access_token(order)

        def build_return_url(status: str) -> str:
            params = {
                "order_id": str(order.id),
                "status": status,
            }
            if guest_access_token:
                params["guest_access_token"] = guest_access_token
            return f"{frontend_url}/checkout/resultado?{urlencode(params)}"

        return {
            "success": build_return_url("approved"),
            "failure": build_return_url("failure"),
            "pending": build_return_url("pending"),
        }

    def _build_booking_back_urls(self, booking: Booking) -> dict[str, str]:
        """Return public back URLs for visit booking redirects."""
        frontend_url = self._resolve_public_base_url(
            settings.FRONTEND_URL,
            setting_name="FRONTEND_URL",
        )
        if not frontend_url:
            return {}

        guest_access_token = build_booking_guest_access_token(booking)

        def build_return_url(status: str) -> str:
            params = {
                "booking_id": str(booking.id),
                "status": status,
            }
            if guest_access_token:
                params["guest_access_token"] = guest_access_token
            return f"{frontend_url}/visitas/resultado?{urlencode(params)}"

        return {
            "success": build_return_url("approved"),
            "failure": build_return_url("failure"),
            "pending": build_return_url("pending"),
        }

    def _build_notification_url(self) -> str | None:
        """Return a public webhook URL when the backend host can receive callbacks."""
        backend_url = self._resolve_public_base_url(
            settings.BACKEND_URL,
            setting_name="BACKEND_URL",
        )
        if not backend_url:
            return None
        return f"{backend_url}/api/v1/payments/webhook/"

    def _build_booking_notification_url(self) -> str | None:
        """Return a public webhook URL for visit booking payments."""
        backend_url = self._resolve_public_base_url(
            settings.BACKEND_URL,
            setting_name="BACKEND_URL",
        )
        if not backend_url:
            return None
        return f"{backend_url}/api/v1/visits/payments/webhook/"

    def _is_local_url(self, value: str) -> bool:
        """Return whether the URL points to a local-only development host."""
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        return hostname in {"localhost", "127.0.0.1", "::1"}

    def _resolve_public_base_url(self, value: str, *, setting_name: str) -> str | None:
        """Return a normalized HTTPS base URL or skip malformed/local values."""
        normalized = str(value or "").strip().rstrip("/")
        if not normalized:
            return None
        if self._is_local_url(normalized):
            return None

        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            logger.warning(
                "mercadopago_public_url_invalid",
                setting=setting_name,
                value=normalized,
            )
            return None
        return normalized

    def _unwrap_response(
        self,
        response: Any,
        *,
        fallback_message: str,
    ) -> dict[str, Any]:
        """Normalize SDK responses and surface a readable API error."""
        if not isinstance(response, dict):
            raise MercadoPagoAPIError("Mercado Pago devolvió una respuesta inválida.")

        status_code = response.get("status")
        body = response.get("response")
        if not isinstance(body, dict):
            body = response if "id" in response else {}

        if isinstance(status_code, int) and status_code >= 400:
            raise MercadoPagoAPIError(self._extract_error_message(body, fallback_message))

        if not body:
            raise MercadoPagoAPIError("Mercado Pago devolvió una respuesta vacía.")

        if body.get("error"):
            raise MercadoPagoAPIError(self._extract_error_message(body, fallback_message))

        return body

    def _extract_error_message(
        self,
        body: dict[str, Any],
        fallback_message: str,
    ) -> str:
        """Build a concise, user-friendly error message from the SDK payload."""
        message = body.get("message")
        error = body.get("error")
        cause = body.get("cause")

        if isinstance(message, str) and message.strip():
            return message.strip()
        if isinstance(error, str) and error.strip():
            return error.strip()
        if isinstance(cause, list) and cause:
            first_cause = cause[0]
            if isinstance(first_cause, dict):
                description = first_cause.get("description")
                if isinstance(description, str) and description.strip():
                    return description.strip()
        return fallback_message

    def _resolve_booking_payer_name(self, booking: Booking) -> tuple[str, str]:
        """Prefer account data and fall back to the booking contact snapshot."""
        first_name = (booking.user.first_name or "").strip() if booking.user_id else ""
        last_name = (booking.user.last_name or "").strip() if booking.user_id else ""
        if first_name or last_name:
            return first_name, last_name
        return booking.customer_first_name.strip() or "Cliente", booking.customer_last_name.strip()

    def _build_booking_preference_items(self, booking: Booking) -> list[dict[str, Any]]:
        """Return Mercado Pago items for a winery visit booking."""
        return [
            {
                "id": f"{booking.time_slot.experience.slug}:{booking.time_slot_id}",
                "title": booking.time_slot.experience.name,
                "description": f"Reserva {booking.confirmation_code}",
                "currency_id": "ARS",
                "quantity": booking.guest_count,
                "unit_price": float(booking.time_slot.experience.price_per_person),
            }
        ]
