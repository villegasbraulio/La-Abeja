"""Tests for transactional outbox and external reconciliation."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.automations.models import OutboxEvent
from apps.automations.tasks.outbox_tasks import process_outbox_event
from apps.automations.tasks.reconciliation_tasks import (
    expire_pending_booking_holds_task,
    reconcile_pending_booking_payments,
    reconcile_pending_payments,
    reconcile_stuck_shipments,
)
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory, OrderItemFactory
from apps.payments.models import Payment
from apps.payments.tests.factories import PaymentFactory
from apps.reservations.models import Booking, BookingPayment, Experience, TimeSlot


def make_experience(**overrides) -> Experience:
    """Create a minimal visit experience for automation tests."""
    defaults = {
        "name": "Visita Reserva",
        "slug": f"visita-{timezone.now().timestamp()}",
        "experience_type": Experience.ExperienceType.WINERY_TOUR,
        "description": "Recorrido guiado",
        "duration_minutes": 90,
        "price_per_person": Decimal("25000.00"),
        "min_guests": 1,
        "max_guests": 12,
        "includes": ["Degustación"],
        "highlights": ["Vista al viñedo"],
        "cover_image": "https://example.com/visit.jpg",
        "gallery_images": [],
        "cancellation_hours": 24,
        "is_active": True,
        "is_featured": False,
    }
    defaults.update(overrides)
    return Experience.objects.create(**defaults)


@pytest.mark.django_db
@patch("apps.orders.fulfillment.send_order_email")
def test_outbox_processes_email_once(mock_send_email) -> None:
    """Completed events should not execute their external action twice."""
    order = OrderFactory()
    OrderItemFactory(order=order)
    event = OutboxEvent.objects.create(
        event_key=f"email-test:{order.id}",
        event_type=OutboxEvent.EventType.ORDER_EMAIL,
        payload={"order_id": str(order.id), "template": "order_status_update"},
    )

    first = process_outbox_event(str(event.id))
    second = process_outbox_event(str(event.id))

    assert first["status"] == OutboxEvent.Status.COMPLETED
    assert second["status"] == "already_completed"
    mock_send_email.assert_called_once()


@pytest.mark.django_db
@patch("apps.reservations.fulfillment.send_booking_email")
def test_outbox_processes_booking_email_once(mock_send_booking_email) -> None:
    """Booking emails should use the same durable outbox worker."""
    experience = make_experience()
    slot = TimeSlot.objects.create(
        experience=experience,
        date=timezone.localdate() + timedelta(days=2),
        start_time=timezone.datetime.strptime("13:00", "%H:%M").time(),
        end_time=timezone.datetime.strptime("14:30", "%H:%M").time(),
        capacity=8,
        spots_available=5,
    )
    booking = Booking.objects.create(
        confirmation_code=Booking.generate_confirmation_code(),
        time_slot=slot,
        customer_first_name="Juan",
        customer_last_name="Paz",
        customer_email="juan@example.com",
        customer_phone="+5492604111111",
        guest_count=3,
        total_price=Decimal("75000.00"),
        status=Booking.Status.PENDING_PAYMENT,
    )
    event = OutboxEvent.objects.create(
        event_key=f"booking-email-test:{booking.id}",
        event_type=OutboxEvent.EventType.BOOKING_EMAIL,
        payload={"booking_id": str(booking.id), "template": "booking_confirmation"},
    )

    first = process_outbox_event(str(event.id))
    second = process_outbox_event(str(event.id))

    assert first["status"] == OutboxEvent.Status.COMPLETED
    assert second["status"] == "already_completed"
    mock_send_booking_email.assert_called_once()


@pytest.mark.django_db
@patch("apps.orders.fulfillment.send_order_email", side_effect=RuntimeError("smtp down"))
def test_outbox_schedules_transient_failure_for_retry(mock_send_email, settings) -> None:
    """Transient provider failures should remain durable for later retry."""
    settings.OUTBOX_MAX_ATTEMPTS = 3
    order = OrderFactory()
    event = OutboxEvent.objects.create(
        event_key=f"email-retry:{order.id}",
        event_type=OutboxEvent.EventType.ORDER_EMAIL,
        payload={"order_id": str(order.id), "template": "order_status_update"},
    )

    result = process_outbox_event(str(event.id))

    event.refresh_from_db()
    assert result["status"] == OutboxEvent.Status.PENDING
    assert event.attempts == 1
    assert event.available_at > timezone.now()
    assert "smtp down" in event.last_error
    mock_send_email.assert_called_once()


@pytest.mark.django_db
@patch("apps.automations.outbox._dispatch_event")
@patch("apps.automations.tasks.reconciliation_tasks.MercadoPagoClient.search_payments")
def test_reconciliation_recovers_missed_approved_payment(
    mock_search_payments,
    mock_dispatch,
    settings,
) -> None:
    """A missed webhook should be recovered by external-reference search."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "token"
    settings.MERCADOPAGO_COLLECTOR_ID = "445566"
    settings.PAYMENT_RECONCILIATION_AGE_MINUTES = 10
    order = OrderFactory(status=Order.Status.PENDING_PAYMENT, total=Decimal("8000.00"))
    OrderItemFactory(order=order)
    payment = PaymentFactory(order=order, amount=order.total, status=Payment.Status.PENDING)
    old_time = timezone.now() - timedelta(minutes=20)
    Payment.objects.filter(pk=payment.pk).update(updated_at=old_time)
    mock_search_payments.return_value = [
        {
            "id": "99880011",
            "status": "approved",
            "external_reference": str(order.id),
            "transaction_amount": "8000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
        }
    ]

    result = reconcile_pending_payments()

    payment.refresh_from_db()
    order.refresh_from_db()
    assert result["payments_synced"] == 1
    assert payment.status == Payment.Status.APPROVED
    assert order.status == Order.Status.PREPARING
    assert OutboxEvent.objects.filter(event_type=OutboxEvent.EventType.ORDER_EMAIL).exists()
    assert OutboxEvent.objects.filter(
        event_type=OutboxEvent.EventType.ANDREANI_FULFILLMENT
    ).exists()


@pytest.mark.django_db
def test_expire_pending_booking_holds_releases_visit_capacity() -> None:
    """Expired visit checkout holds should release their seats."""
    experience = make_experience()
    slot = TimeSlot.objects.create(
        experience=experience,
        date=timezone.localdate() + timedelta(days=2),
        start_time=timezone.datetime.strptime("13:00", "%H:%M").time(),
        end_time=timezone.datetime.strptime("14:30", "%H:%M").time(),
        capacity=8,
        spots_available=5,
    )
    booking = Booking.objects.create(
        confirmation_code=Booking.generate_confirmation_code(),
        time_slot=slot,
        customer_first_name="Juan",
        customer_last_name="Paz",
        customer_email="juan@example.com",
        customer_phone="+5492604111111",
        guest_count=3,
        total_price=Decimal("75000.00"),
        status=Booking.Status.PENDING_PAYMENT,
        hold_expires_at=timezone.now() - timedelta(minutes=1),
    )
    payment = BookingPayment.objects.create(
        booking=booking,
        idempotency_key=f"mercadopago:booking:{booking.id}",
        amount=booking.total_price,
        currency="ARS",
        status=BookingPayment.Status.PENDING,
    )

    result = expire_pending_booking_holds_task()

    booking.refresh_from_db()
    payment.refresh_from_db()
    slot.refresh_from_db()
    assert result["booking_holds_expired"] == 1
    assert booking.status == Booking.Status.PAYMENT_FAILED
    assert payment.status == BookingPayment.Status.CANCELLED
    assert payment.status_detail == "booking_hold_expired"
    assert slot.spots_available == 8


@pytest.mark.django_db
@patch("apps.automations.tasks.reconciliation_tasks.MercadoPagoClient.search_payments")
def test_reconciliation_recovers_missed_booking_payment(mock_search_payments, settings) -> None:
    """A missed visit payment webhook should be recovered by external-reference search."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "token"
    settings.MERCADOPAGO_COLLECTOR_ID = "445566"
    settings.BOOKING_PAYMENT_RECONCILIATION_AGE_MINUTES = 5
    experience = make_experience()
    slot = TimeSlot.objects.create(
        experience=experience,
        date=timezone.localdate() + timedelta(days=2),
        start_time=timezone.datetime.strptime("13:00", "%H:%M").time(),
        end_time=timezone.datetime.strptime("14:30", "%H:%M").time(),
        capacity=8,
        spots_available=5,
    )
    booking = Booking.objects.create(
        confirmation_code=Booking.generate_confirmation_code(),
        time_slot=slot,
        customer_first_name="Juan",
        customer_last_name="Paz",
        customer_email="juan@example.com",
        customer_phone="+5492604111111",
        guest_count=3,
        total_price=Decimal("75000.00"),
        status=Booking.Status.PENDING_PAYMENT,
        hold_expires_at=timezone.now() + timedelta(minutes=10),
    )
    payment = BookingPayment.objects.create(
        booking=booking,
        idempotency_key=f"mercadopago:booking:{booking.id}",
        amount=booking.total_price,
        currency="ARS",
        status=BookingPayment.Status.PENDING,
    )
    BookingPayment.objects.filter(pk=payment.pk).update(
        updated_at=timezone.now() - timedelta(minutes=20)
    )
    mock_search_payments.return_value = [
        {
            "id": "99880022",
            "status": "approved",
            "external_reference": str(booking.id),
            "transaction_amount": "75000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
        }
    ]

    result = reconcile_pending_booking_payments()

    booking.refresh_from_db()
    payment.refresh_from_db()
    slot.refresh_from_db()
    assert result["booking_payments_synced"] == 1
    assert booking.status == Booking.Status.CONFIRMED
    assert payment.status == BookingPayment.Status.APPROVED
    assert slot.spots_available == 5


@pytest.mark.django_db
@patch("apps.automations.outbox._dispatch_event")
def test_reconciliation_requeues_paid_order_without_shipment(mock_dispatch, settings) -> None:
    """Paid orders missing tracking should be restored to the outbox."""
    settings.SHIPMENT_RECONCILIATION_AGE_MINUTES = 10
    order = OrderFactory(
        status=Order.Status.PREPARING,
        shipping_method=Order.ShippingMethod.STANDARD,
    )
    Order.objects.filter(pk=order.pk).update(
        updated_at=timezone.now() - timedelta(minutes=20)
    )

    result = reconcile_stuck_shipments()

    assert result["shipments_requeued"] == 1
    assert OutboxEvent.objects.filter(
        event_key=f"andreani-fulfillment:{order.id}",
        status=OutboxEvent.Status.PENDING,
    ).exists()
