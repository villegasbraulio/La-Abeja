"""Reservation domain services."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Booking, BookingManualRefund, BookingPayment, TimeSlot

CAPACITY_CONFIRMED_STATUSES = {
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
    return status in CAPACITY_CONFIRMED_STATUSES


def booking_holds_capacity(booking: Booking, *, now=None) -> bool:
    """Return whether a booking currently consumes slot capacity."""
    if booking.status in CAPACITY_CONFIRMED_STATUSES:
        return True
    if booking.status != Booking.Status.PENDING_PAYMENT:
        return False
    if booking.hold_expires_at is None:
        return False
    current = now or timezone.now()
    return booking.hold_expires_at > current


def recalculate_slot_availability(slot: TimeSlot) -> int:
    """Persist the slot availability from the bookings that currently hold seats."""
    current = timezone.now()
    reserved = (
        slot.bookings.filter(
            Q(status__in=CAPACITY_CONFIRMED_STATUSES)
            | Q(status=Booking.Status.PENDING_PAYMENT, hold_expires_at__gt=current)
        )
        .aggregate(total=Coalesce(Sum("guest_count"), 0))
        .get("total", 0)
    )
    available = slot.capacity - int(reserved or 0)
    if available < 0:
        raise ReservationCapacityError(
            "La capacidad del turno quedó por debajo de las reservas activas."
        )

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


def booking_cancellation_deadline(booking: Booking):
    """Return the latest time a customer can cancel without staff override."""
    slot_start = timezone.make_aware(
        datetime.combine(booking.time_slot.date, booking.time_slot.start_time),
        timezone.get_current_timezone(),
    )
    return slot_start - timedelta(hours=booking.time_slot.experience.cancellation_hours)


def can_cancel_booking(booking: Booking, *, now=None) -> bool:
    """Return whether the booking is still inside the configured cancellation window."""
    if booking.status not in {Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED}:
        return False
    return (now or timezone.now()) <= booking_cancellation_deadline(booking)


def ensure_manual_refund_record(
    booking: Booking,
    *,
    operator=None,
    note: str = "",
    reason: str = "booking_cancelled",
) -> BookingManualRefund | None:
    """Create or update the internal manual refund task for an approved booking payment."""
    try:
        payment = booking.payment
    except BookingPayment.DoesNotExist:
        return None

    if payment.status != BookingPayment.Status.APPROVED:
        return None

    refund, created = BookingManualRefund.objects.get_or_create(
        booking=booking,
        defaults={
            "payment": payment,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": BookingManualRefund.Status.PENDING,
            "reason": reason,
            "note": note,
            "operator": operator if getattr(operator, "is_authenticated", False) else None,
        },
    )
    update_fields: list[str] = []
    if not created and note and refund.note != note:
        refund.note = note
        update_fields.append("note")
    if not created and operator and getattr(operator, "is_authenticated", False):
        refund.operator = operator
        update_fields.append("operator")
    if not created and refund.payment_id is None:
        refund.payment = payment
        update_fields.append("payment")
    if update_fields:
        update_fields.append("updated_at")
        refund.save(update_fields=update_fields)
    return refund


def mark_manual_refund(
    refund: BookingManualRefund,
    *,
    status: str | None = None,
    note: str | None = None,
    operator=None,
) -> BookingManualRefund:
    """Update staff-managed refund state with audit context."""
    update_fields: list[str] = []
    if status:
        refund.status = status
        update_fields.append("status")
        if status == BookingManualRefund.Status.COMPLETED and refund.completed_at is None:
            refund.completed_at = timezone.now()
            update_fields.append("completed_at")
        if status != BookingManualRefund.Status.COMPLETED and refund.completed_at is not None:
            refund.completed_at = None
            update_fields.append("completed_at")
    if note is not None:
        refund.note = note.strip()
        update_fields.append("note")
    if operator and getattr(operator, "is_authenticated", False):
        refund.operator = operator
        update_fields.append("operator")
    if update_fields:
        update_fields.append("updated_at")
        refund.save(update_fields=update_fields)
    return refund


def cancel_booking(
    booking: Booking,
    *,
    actor=None,
    note: str = "",
    enforce_deadline: bool = True,
) -> tuple[Booking, BookingManualRefund | None]:
    """Cancel a booking, release capacity and create the manual refund task if needed."""
    if enforce_deadline and not can_cancel_booking(booking):
        raise ReservationIntegrityError("La reserva solo se puede cancelar hasta 24 hs antes.")

    slot = TimeSlot.objects.select_for_update().get(pk=booking.time_slot_id)
    booking.status = Booking.Status.CANCELLED
    booking.hold_expires_at = None
    booking.save(update_fields=["status", "hold_expires_at"])

    try:
        payment = booking.payment
    except BookingPayment.DoesNotExist:
        payment = None
    if payment and payment.status in {
        BookingPayment.Status.PENDING,
        BookingPayment.Status.IN_PROCESS,
    }:
        payment.status = BookingPayment.Status.CANCELLED
        payment.status_detail = "booking_cancelled"
        payment.save(update_fields=["status", "status_detail", "updated_at"])

    refund = ensure_manual_refund_record(booking, operator=actor, note=note)
    recalculate_slot_availability(slot)
    return booking, refund


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


def _booking_has_confirmation_capacity(booking: Booking, slot: TimeSlot) -> bool:
    """Return whether an approved payment can safely confirm the booking."""
    if booking_holds_capacity(booking):
        return True
    current_available = recalculate_slot_availability(slot)
    return booking.guest_count <= current_available


@transaction.atomic
def expire_pending_booking_holds(*, now=None) -> dict[str, int]:
    """Expire pending bookings whose payment window has elapsed."""
    current = now or timezone.now()
    bookings = list(
        Booking.objects.select_for_update()
        .select_related("time_slot")
        .filter(
            status=Booking.Status.PENDING_PAYMENT,
            hold_expires_at__isnull=False,
            hold_expires_at__lte=current,
        )
        .order_by("hold_expires_at")
    )
    if not bookings:
        return {"booking_holds_expired": 0, "slots_recalculated": 0}

    slot_ids: set[int] = set()
    booking_ids = [booking.id for booking in bookings]
    for booking in bookings:
        booking.status = Booking.Status.PAYMENT_FAILED
        booking.hold_expires_at = None
        booking.save(update_fields=["status", "hold_expires_at"])
        slot_ids.add(booking.time_slot_id)

    BookingPayment.objects.filter(
        booking_id__in=booking_ids,
        status__in=[BookingPayment.Status.PENDING, BookingPayment.Status.IN_PROCESS],
    ).update(
        status=BookingPayment.Status.CANCELLED,
        status_detail="booking_hold_expired",
        updated_at=current,
    )

    slots_recalculated = 0
    for slot in TimeSlot.objects.select_for_update().filter(pk__in=slot_ids):
        recalculate_slot_availability(slot)
        slots_recalculated += 1

    return {
        "booking_holds_expired": len(bookings),
        "slots_recalculated": slots_recalculated,
    }


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

    if mapped_payment_status == BookingPayment.Status.APPROVED:
        if booking.status not in {
            Booking.Status.CANCELLED,
            Booking.Status.COMPLETED,
            Booking.Status.NO_SHOW,
        } and not _booking_has_confirmation_capacity(booking, slot):
            booking.status = Booking.Status.PAYMENT_FAILED
            booking.hold_expires_at = None
            booking.save(update_fields=["status", "hold_expires_at"])
            payment.status_detail = "capacity_unavailable_after_payment"
            payment.save(update_fields=["status_detail", "updated_at"])
            recalculate_slot_availability(slot)
            return payment

    if next_booking_status != booking.status:
        booking.status = next_booking_status
        if next_booking_status != Booking.Status.PENDING_PAYMENT:
            booking.hold_expires_at = None
            booking.save(update_fields=["status", "hold_expires_at"])
        else:
            booking.save(update_fields=["status"])

    recalculate_slot_availability(slot)
    return payment
