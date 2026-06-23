"""Payment integrity validation and transactional state synchronization."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.catalog.models import Wine
from apps.orders.models import Order
from apps.orders.state_machine import can_transition

from .models import Payment

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


class PaymentIntegrityError(Exception):
    """Raised when Mercado Pago data does not match the local order."""


def resolve_order_status(current_order_status: str, payment_status: str) -> str:
    """Map payment state into an allowed order state transition."""
    next_status = ORDER_STATUS_MAP.get(payment_status, current_order_status)
    if next_status == current_order_status:
        return current_order_status
    if can_transition(current_order_status, next_status):
        return next_status
    return current_order_status


def validate_approved_payment(payment: Payment, payment_data: dict[str, Any]) -> None:
    """Verify the immutable payment identity before approving an order."""
    if str(payment_data.get("status") or "").lower() != "approved":
        return

    errors: list[str] = []
    external_reference = str(payment_data.get("external_reference") or "")
    if external_reference != str(payment.order_id):
        errors.append("external_reference")

    try:
        remote_amount = Decimal(str(payment_data.get("transaction_amount")))
    except (InvalidOperation, TypeError):
        remote_amount = Decimal("-1")
    if remote_amount != payment.amount:
        errors.append("transaction_amount")

    if str(payment_data.get("currency_id") or "").upper() != payment.currency.upper():
        errors.append("currency_id")

    expected_collector_id = str(settings.MERCADOPAGO_COLLECTOR_ID or "").strip()
    remote_collector_id = str(payment_data.get("collector_id") or "").strip()
    if not expected_collector_id or remote_collector_id != expected_collector_id:
        errors.append("collector_id")

    if errors:
        raise PaymentIntegrityError(
            "El pago aprobado no coincide con el pedido: " + ", ".join(errors)
        )


@transaction.atomic
def sync_payment(payment_id: object, payment_data: dict[str, Any]) -> Payment:
    """Apply a verified Mercado Pago state while locking payment and order."""
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    order = Order.objects.select_for_update().get(pk=payment.order_id)
    validate_approved_payment(payment, payment_data)

    raw_status = str(payment_data.get("status") or "pending").lower()
    mapped_payment_status = PAYMENT_STATUS_MAP.get(raw_status, Payment.Status.PENDING)
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
    return payment
