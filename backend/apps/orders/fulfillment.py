"""External order fulfillment operations executed by outbox workers."""

from __future__ import annotations

from urllib.parse import urlsplit

import structlog
from django.core.files.base import ContentFile

from apps.notifications.email import EmailService

from .andreani import AndreaniAPIError, AndreaniClient
from .models import AndreaniShipment, Order
from .shipping import build_tracking_url

logger = structlog.get_logger(__name__)


class PermanentFulfillmentError(Exception):
    """Raised when retrying an external fulfillment operation cannot help."""


def send_order_email(order: Order, *, template: str) -> None:
    """Send an order email and surface delivery failures to the outbox."""
    if not order.customer_email:
        return
    items_summary = " | ".join(
        f"{item.quantity}x {item.wine_name} ({item.subtotal})" for item in order.items.all()
    )
    sent = EmailService.send_transactional(
        to=order.customer_email,
        template=template,
        context={
            "order_number": order.order_number,
            "status": order.get_status_display(),
            "total": order.total,
            "shipping_method": order.get_shipping_method_display(),
            "estimated_delivery": order.estimated_delivery or "A coordinar",
            "tracking_number": order.tracking_number or "Pendiente de asignación",
            "tracking_url": build_tracking_url(order.tracking_number) or "Pendiente",
            "items": items_summary,
        },
    )
    if not sent:
        raise RuntimeError("No se pudo enviar el email transaccional del pedido.")


def sync_andreani_shipping_order(
    order: Order,
    *,
    retry_failed: bool = False,
) -> AndreaniShipment | None:
    """Idempotently create a shipment and persist its label."""
    if (
        order.status not in {Order.Status.PAID, Order.Status.PREPARING}
        or order.shipping_method == Order.ShippingMethod.PICKUP
    ):
        return None

    existing_record = AndreaniShipment.objects.filter(order=order).first()
    if order.tracking_number and existing_record is None:
        return None

    audit_record, created = AndreaniShipment.objects.get_or_create(
        order=order,
        defaults={
            "idempotency_key": f"andreani:order:{order.id}",
            "status": AndreaniShipment.Status.PROCESSING,
        },
    )
    client = AndreaniClient()

    if not created and audit_record.status == AndreaniShipment.Status.CREATED:
        if audit_record.tracking_number and order.tracking_number != audit_record.tracking_number:
            order.tracking_number = audit_record.tracking_number
            order.save(update_fields=["tracking_number", "updated_at"])
        if not audit_record.label:
            _store_andreani_label(client, audit_record)
        return audit_record

    if not created and audit_record.status == AndreaniShipment.Status.FAILED:
        retriable = (
            audit_record.response_status_code is None
            or audit_record.response_status_code >= 500
        )
        if not retry_failed or not retriable:
            if retriable:
                raise AndreaniAPIError(audit_record.last_error or "Envío Andreani fallido.")
            raise PermanentFulfillmentError(audit_record.last_error or "Andreani rechazó el envío.")
        audit_record.status = AndreaniShipment.Status.PROCESSING
        audit_record.last_error = ""
        audit_record.save(update_fields=["status", "last_error", "updated_at"])

    payload = client._build_payload(order)
    audit_record.request_payload = payload
    audit_record.save(update_fields=["request_payload", "updated_at"])
    try:
        shipment = client.create_shipping_order(order, payload=payload)
    except AndreaniAPIError as exc:
        audit_record.status = AndreaniShipment.Status.FAILED
        audit_record.raw_response = exc.response_body if exc.response_body is not None else {}
        audit_record.response_status_code = exc.status_code
        audit_record.attempt_count += exc.attempt_count
        audit_record.last_error = str(exc)
        audit_record.save(
            update_fields=[
                "status",
                "raw_response",
                "response_status_code",
                "attempt_count",
                "last_error",
                "updated_at",
            ]
        )
        if not exc.retriable:
            raise PermanentFulfillmentError(str(exc)) from exc
        raise

    tracking_number = str(shipment.get("tracking_number") or "").strip()
    audit_record.status = AndreaniShipment.Status.CREATED
    audit_record.tracking_number = tracking_number
    audit_record.raw_response = shipment.get("raw_response") or {}
    audit_record.response_status_code = client.last_status_code
    audit_record.attempt_count += client.last_attempt_count
    audit_record.label_source_url = str(shipment.get("shipment_label") or "")
    audit_record.last_error = ""
    audit_record.save(
        update_fields=[
            "status",
            "tracking_number",
            "raw_response",
            "response_status_code",
            "attempt_count",
            "label_source_url",
            "last_error",
            "updated_at",
        ]
    )

    shipping_address = dict(order.shipping_address)
    shipping_address["_andreani_order"] = {
        "tracking_number": tracking_number,
        "shipment_status": shipment.get("shipment_status"),
        "shipment_type": shipment.get("shipment_type"),
        "shipment_label": shipment.get("shipment_label"),
    }
    update_fields = ["shipping_address", "updated_at"]
    order.shipping_address = shipping_address
    if tracking_number:
        order.tracking_number = tracking_number
        update_fields.append("tracking_number")
    if shipment.get("estimated_delivery"):
        order.estimated_delivery = shipment["estimated_delivery"]
        update_fields.append("estimated_delivery")
    order.save(update_fields=update_fields)

    _store_andreani_label(client, audit_record)
    return audit_record


def _store_andreani_label(client: AndreaniClient, audit_record: AndreaniShipment) -> None:
    """Copy a remote label into Django storage and surface failures."""
    if not audit_record.label_source_url:
        message = "La respuesta de Andreani no incluyó una URL de etiqueta."
        audit_record.label_error = message
        audit_record.save(update_fields=["label_error", "updated_at"])
        raise PermanentFulfillmentError(message)
    try:
        label_content = client.download_label(audit_record.label_source_url)
    except AndreaniAPIError as exc:
        audit_record.label_error = str(exc)
        audit_record.save(update_fields=["label_error", "updated_at"])
        raise

    extension = ".zpl" if urlsplit(audit_record.label_source_url).path.endswith(".zpl") else ".pdf"
    filename = f"{audit_record.order.order_number}-{audit_record.tracking_number}{extension}"
    audit_record.label.save(filename, ContentFile(label_content), save=False)
    audit_record.label_error = ""
    audit_record.save(update_fields=["label", "label_error", "updated_at"])
