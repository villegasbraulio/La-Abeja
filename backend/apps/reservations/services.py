"""Reservation domain services."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import Booking, BookingPayment, TimeSlot

CAPACITY_HOLDING_STATUSES = {
    Booking.Status.PENDING_PAYMENT,
    Booking.Status.CONFIRMED,
    Booking.Status.COMPLETED,
    Booking.Status.NO_SHOW,
}

PAYMENT_STATUS_MAP: dict[str, str] = {
    "approved": BookingPayment.Status.APPROVED,
    "in_process": BookingPayment.Status.IN_PROCESS,
    "pending": BookingPayment.Status.PENDING,
    "authorized": BookingPayment.Status.PENDING,
    "rejected": BookingPayment.Status.REJECTED,
    "cancelled": BookingPayment.Status.CANCELLED,
    "refunded": BookingPayment.Status.REFUNDED,
    "charged_back": BookingPayment.Status.REFUNDED,
}


class ReservationCapacityError(Exception):
    """Raised when a slot does not have enough free seats."""


class ReservationIntegrityError(Exception):
    """Raised when Mercado Pago data does not match the local booking."""


def booking_consumes_capacity(status: str) -> bool:
    """Return whether a booking status should occupy a seat."""
    return status in CAPACITY_HOLDING_STATUSES


def recalculate_slot_availability(slot: TimeSlot) -> int:
    """Persist the slot availability from the bookings that currently hold seats."""
    reserved = (
        slot.bookings.filter(status__in=CAPACITY_HOLDING_STATUSES)
        .aggregate(total=Coalesce(Sum("guest_count"), 0))
        .get("total", 0)
    )
    available = slot.capacity - int(reserved or 0)
    if available < 0:
        raise ReservationCapacityError("La capacidad del turno quedó por debajo de las reservas activas.")

    if slot.spots_available != available:
        slot.spots_available = available
        slot.save(update_fields=["spots_available"])
    return available


def resolve_booking_status(current_status: str, payment_status: str) -> str:
    """Map booking payment state into the next booking state."""
    if current_status in {
        Booking.Status.CANCELLED,
        Booking.Status.COMPLETED,
        Booking.Status.NO_SHOW,
    }:
        return current_status

    if payment_status == BookingPayment.Status.APPROVED:
        return Booking.Status.CONFIRMED

    if payment_status in {
        BookingPayment.Status.REJECTED,
        BookingPayment.Status.CANCELLED,
        BookingPayment.Status.REFUNDED,
    }:
        return Booking.Status.PAYMENT_FAILED

    return Booking.Status.PENDING_PAYMENT


def validate_approved_booking_payment(
    payment: BookingPayment,
    payment_data: dict[str, Any],
) -> None:
    """Verify the immutable payment identity before approving a booking."""
    if str(payment_data.get("status") or "").lower() != "approved":
        return

    errors: list[str] = []
    external_reference = str(payment_data.get("external_reference") or "")
    if external_reference != str(payment.booking_id):
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
        raise ReservationIntegrityError(
            "El pago aprobado no coincide con la reserva: " + ", ".join(errors)
        )


@transaction.atomic
def sync_booking_payment(payment_id: object, payment_data: dict[str, Any]) -> BookingPayment:
    """Apply a verified Mercado Pago state to the booking and its slot."""
    payment = (
        BookingPayment.objects.select_for_update()
        .select_related("booking", "booking__time_slot")
        .get(pk=payment_id)
    )
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    slot = TimeSlot.objects.select_for_update().get(pk=booking.time_slot_id)
    validate_approved_booking_payment(payment, payment_data)

    raw_status = str(payment_data.get("status") or "pending").lower()
    mapped_payment_status = PAYMENT_STATUS_MAP.get(raw_status, BookingPayment.Status.PENDING)
    next_booking_status = resolve_booking_status(booking.status, mapped_payment_status)

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

    if next_booking_status != booking.status:
        booking.status = next_booking_status
        booking.save(update_fields=["status"])

    recalculate_slot_availability(slot)
    return payment
