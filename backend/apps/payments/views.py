"""Views for Mercado Pago payment flows."""

from __future__ import annotations

from typing import Any

import structlog
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .mercadopago import MercadoPagoAPIError, MercadoPagoClient
from .models import Payment, PaymentWebhookLog
from .serializers import CreatePreferenceSerializer
from .services import PaymentIntegrityError, sync_payment
from .webhook_utils import build_webhook_deduplication_key, has_valid_signature

logger = structlog.get_logger(__name__)


class CreatePreferenceView(APIView):
    """Create a Mercado Pago Checkout Pro preference for an order."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Return the redirect URL for Mercado Pago Checkout Pro."""
        serializer = CreatePreferenceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            payload = serializer.create_preference()
        except MercadoPagoAPIError as exc:
            logger.error("mercadopago_preference_failed", error=str(exc))
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(payload, status=status.HTTP_201_CREATED)


class PaymentWebhookView(APIView):
    """Receive Mercado Pago payment notifications."""

    permission_classes = [permissions.AllowAny]

    def _is_simulation_payload(self, payload: dict[str, Any]) -> bool:
        """Detect Mercado Pago simulation payloads that do not map to a real payment."""
        return payload.get("live_mode") is False

    def post(self, request: Request) -> Response:
        """Persist the raw webhook, validate it and sync payment state."""
        payload = request.data if isinstance(request.data, dict) else {}
        topic = str(request.query_params.get("type") or payload.get("type") or "")
        notification_id = str(
            payload.get("id")
            or request.query_params.get("id")
            or request.query_params.get("data.id")
            or (payload.get("data") or {}).get("id")
            or "unknown"
        )
        payment_resource_id = request.query_params.get("data.id") or str(
            (payload.get("data") or {}).get("id", "")
        )
        deduplication_key = build_webhook_deduplication_key(
            topic=topic or "unknown",
            notification_id=notification_id,
            payment_resource_id=payment_resource_id,
            payload=payload,
        )
        webhook_log, created = PaymentWebhookLog.objects.get_or_create(
            deduplication_key=deduplication_key,
            defaults={
                "mp_notification_id": notification_id,
                "topic": topic or "unknown",
                "payload": payload,
            },
        )
        if not created and webhook_log.processed:
            return Response(status=status.HTTP_200_OK)

        try:
            if not has_valid_signature(request, payload):
                webhook_log.error = "invalid_signature"
                webhook_log.save(update_fields=["error"])
                logger.warning(
                    "mercadopago_webhook_invalid_signature",
                    notification_id=notification_id,
                )
                return Response(status=status.HTTP_403_FORBIDDEN)

            if topic != "payment":
                webhook_log.processed = True
                webhook_log.save(update_fields=["processed"])
                return Response(status=status.HTTP_200_OK)

            if not payment_resource_id:
                webhook_log.error = "missing_payment_id"
                webhook_log.save(update_fields=["error"])
                return Response(status=status.HTTP_200_OK)

            payment_data = MercadoPagoClient().get_payment(str(payment_resource_id))
            payment = self._find_payment(payment_data)
            if payment is None:
                webhook_log.error = "payment_not_found"
                webhook_log.save(update_fields=["error"])
                logger.warning(
                    "mercadopago_payment_not_found",
                    notification_id=notification_id,
                    payment_id=payment_resource_id,
                )
                return Response(status=status.HTTP_200_OK)

            sync_payment(payment.pk, payment_data)
            webhook_log.processed = True
            webhook_log.error = ""
            webhook_log.save(update_fields=["processed", "error"])
        except PaymentIntegrityError as exc:
            Payment.objects.filter(pk=payment.pk).update(
                status_detail="integrity_validation_failed"
            )
            webhook_log.error = f"payment_integrity_error: {exc}"
            webhook_log.processed = True
            webhook_log.save(update_fields=["error", "processed"])
            logger.error(
                "mercadopago_payment_integrity_failed",
                notification_id=notification_id,
                payment_id=payment_resource_id,
                error=str(exc),
            )
            return Response(status=status.HTTP_200_OK)
        except MercadoPagoAPIError as exc:
            webhook_log.error = str(exc)
            error_message = str(exc).lower()
            if self._is_simulation_payload(payload) or "not found" in error_message:
                webhook_log.processed = True
                webhook_log.save(update_fields=["error", "processed"])
                logger.info(
                    "mercadopago_webhook_simulation_ignored",
                    notification_id=notification_id,
                    payment_id=payment_resource_id,
                    error=str(exc),
                )
                return Response(status=status.HTTP_200_OK)

            webhook_log.save(update_fields=["error"])
            logger.error("mercadopago_webhook_fetch_failed", error=str(exc))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:  # pragma: no cover - defensive logging
            webhook_log.error = str(exc)
            webhook_log.save(update_fields=["error"])
            logger.error("mercadopago_webhook_failed", error=str(exc))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    def _find_payment(self, payment_data: dict[str, Any]) -> Payment | None:
        """Locate the local payment record from Mercado Pago payment data."""
        external_reference = str(payment_data.get("external_reference") or "")
        metadata = payment_data.get("metadata") or {}
        order_id = external_reference or str(metadata.get("order_id") or "")
        if order_id:
            return Payment.objects.select_related("order").filter(order_id=order_id).first()

        preference_id = str(payment_data.get("metadata", {}).get("preference_id") or "")
        if preference_id:
            return (
                Payment.objects.select_related("order")
                .filter(mp_preference_id=preference_id)
                .first()
            )
        return None
