"""Periodic reconciliation for missed payment and shipment callbacks."""

from __future__ import annotations

from datetime import timedelta

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.automations.models import OutboxEvent
from apps.automations.outbox import enqueue_outbox_event
from apps.orders.models import AndreaniShipment, Order
from apps.payments.mercadopago import MercadoPagoAPIError, MercadoPagoClient
from apps.payments.models import Payment
from apps.payments.services import PaymentIntegrityError, sync_payment

logger = structlog.get_logger(__name__)


@shared_task
def reconcile_external_operations() -> dict[str, int]:
    """Recover pending payments and missing Andreani fulfillment work."""
    payment_result = reconcile_pending_payments()
    shipment_result = reconcile_stuck_shipments()
    return {**payment_result, **shipment_result}


@shared_task
def reconcile_pending_payments() -> dict[str, int]:
    """Pull current Mercado Pago state when a webhook was missed."""
    threshold = timezone.now() - timedelta(minutes=settings.PAYMENT_RECONCILIATION_AGE_MINUTES)
    payments = list(
        Payment.objects.filter(
            status__in=[Payment.Status.PENDING, Payment.Status.IN_PROCESS],
            updated_at__lte=threshold,
        )
        .exclude(status_detail="integrity_validation_failed")
        .select_related("order")
    )
    if not payments:
        return {"payments_checked": 0, "payments_synced": 0, "payment_errors": 0}

    client = MercadoPagoClient()
    synced = 0
    errors = 0
    for payment in payments:
        try:
            if payment.mp_payment_id:
                payment_data = client.get_payment(payment.mp_payment_id)
            else:
                candidates = client.search_payments(external_reference=str(payment.order_id))
                if not candidates:
                    continue
                payment_data = candidates[0]
            sync_payment(payment.pk, payment_data)
            synced += 1
        except PaymentIntegrityError as exc:
            Payment.objects.filter(pk=payment.pk).update(
                status_detail="integrity_validation_failed"
            )
            errors += 1
            logger.error(
                "payment_reconciliation_integrity_failed",
                payment_id=str(payment.id),
                error=str(exc),
            )
        except MercadoPagoAPIError as exc:
            errors += 1
            logger.error(
                "payment_reconciliation_failed",
                payment_id=str(payment.id),
                error=str(exc),
            )
    return {
        "payments_checked": len(payments),
        "payments_synced": synced,
        "payment_errors": errors,
    }


@shared_task
def reconcile_stuck_shipments() -> dict[str, int]:
    """Requeue paid orders missing tracking or a stored label."""
    threshold = timezone.now() - timedelta(minutes=settings.SHIPMENT_RECONCILIATION_AGE_MINUTES)
    orders = (
        Order.objects.filter(status=Order.Status.PAID, updated_at__lte=threshold)
        .exclude(shipping_method=Order.ShippingMethod.PICKUP)
        .order_by("updated_at")
    )
    requeued = 0
    for order in orders:
        try:
            shipment = order.andreani_shipment
        except AndreaniShipment.DoesNotExist:
            shipment = None

        if shipment is None and order.tracking_number:
            continue
        if shipment and shipment.status == AndreaniShipment.Status.FAILED:
            if shipment.response_status_code is not None and shipment.response_status_code < 500:
                continue
        if (
            shipment
            and shipment.status == AndreaniShipment.Status.CREATED
            and shipment.label
            and order.tracking_number
        ):
            continue

        enqueue_outbox_event(
            event_key=f"andreani-fulfillment:{order.id}",
            event_type=OutboxEvent.EventType.ANDREANI_FULFILLMENT,
            payload={"order_id": str(order.id)},
            revive=True,
        )
        requeued += 1
    return {"shipments_checked": orders.count(), "shipments_requeued": requeued}
