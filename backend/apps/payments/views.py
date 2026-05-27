"""Views for Mercado Pago payment flows."""

from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta
from typing import Any

import structlog
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Wine
from apps.orders.models import Order
from apps.orders.state_machine import can_transition

from .mercadopago import MercadoPagoAPIError, MercadoPagoClient
from .models import Payment, PaymentWebhookLog
from .serializers import CreatePreferenceSerializer

logger = structlog.get_logger(__name__)

PAYMENT_STATUS_MAP: dict[str, str] = {
    "approved": Payment.Status.APPROVED,
    "in_process": Payment.Status.IN_PROCESS,
    "pending": Payment.Status.PENDING,
    "authorized": Payment.Status.PENDING,
    "rejected": Payment.Status.REJECTED,
    "cancelled": Payment.Status.CANCELLED,
    "refunded": Payment.Status.REFUNDED,
    "charged_back": Payment.Status.REFUNDED,
}

ORDER_STATUS_MAP: dict[str, str] = {
    Payment.Status.APPROVED: Order.Status.PAID,
    Payment.Status.REJECTED: Order.Status.PAYMENT_FAILED,
    Payment.Status.CANCELLED: Order.Status.PAYMENT_FAILED,
    Payment.Status.REFUNDED: Order.Status.REFUNDED,
}


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


def resolve_order_status(current_order_status: str, payment_status: str) -> str:
    """Map payment state into an allowed order state transition."""
    next_status = ORDER_STATUS_MAP.get(payment_status, current_order_status)
    if next_status == current_order_status:
        return current_order_status
    if can_transition(current_order_status, next_status):
        return next_status
    return current_order_status


class CreatePreferenceView(APIView):
    """Create a Mercado Pago Checkout Pro preference for an order."""

    permission_classes = [permissions.IsAuthenticated]

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
        webhook_log = PaymentWebhookLog.objects.create(
            mp_notification_id=notification_id,
            topic=topic or "unknown",
            payload=payload,
        )

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

            payment_resource_id = request.query_params.get("data.id") or str(
                (payload.get("data") or {}).get("id", "")
            )
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

            self._sync_payment(payment, payment_data)
            webhook_log.processed = True
            webhook_log.save(update_fields=["processed"])
        except MercadoPagoAPIError as exc:
            webhook_log.error = str(exc)
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

    @transaction.atomic
    def _sync_payment(self, payment: Payment, payment_data: dict[str, Any]) -> None:
        """Apply Mercado Pago payment state to local payment and order records."""
        raw_status = str(payment_data.get("status") or "pending").lower()
        mapped_payment_status = PAYMENT_STATUS_MAP.get(raw_status, Payment.Status.PENDING)
        order = payment.order
        next_order_status = resolve_order_status(order.status, mapped_payment_status)

        payment.mp_payment_id = str(payment_data.get("id") or payment.mp_payment_id)
        payment.mp_merchant_order_id = str(
            (payment_data.get("order") or {}).get("id") or payment.mp_merchant_order_id
        )
        payment.status = mapped_payment_status
        payment.status_detail = str(payment_data.get("status_detail") or "")
        payment.payment_method = str(payment_data.get("payment_method_id") or "")
        payment.payment_type = str(payment_data.get("payment_type_id") or "")
        payment.installments = int(payment_data.get("installments") or payment.installments or 1)
        payment.save(
            update_fields=[
                "mp_payment_id",
                "mp_merchant_order_id",
                "status",
                "status_detail",
                "payment_method",
                "payment_type",
                "installments",
                "updated_at",
            ]
        )

        if next_order_status != order.status:
            previous_status = order.status
            order.status = next_order_status
            if next_order_status == Order.Status.PAID and not order.estimated_delivery:
                if order.shipping_method == Order.ShippingMethod.STANDARD:
                    order.estimated_delivery = timezone.localdate() + timedelta(days=7)
                elif order.shipping_method == Order.ShippingMethod.EXPRESS:
                    order.estimated_delivery = timezone.localdate() + timedelta(days=3)
            order.save(update_fields=["status", "estimated_delivery", "updated_at"])

            if previous_status != Order.Status.PAID and next_order_status == Order.Status.PAID:
                for item in order.items.select_related("wine").all():
                    Wine.objects.filter(id=item.wine_id).update(
                        stock=models.F("stock") - item.quantity
                    )

        logger.info(
            "mercadopago_payment_synced",
            order_id=str(order.id),
            payment_id=payment.mp_payment_id,
            payment_status=payment.status,
            order_status=order.status,
        )
