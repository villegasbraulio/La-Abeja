"""Public visit booking API coverage."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.payments.models import PaymentWebhookLog
from apps.reservations.access import build_guest_access_token
from apps.reservations.models import Booking, BookingPayment, Experience, TimeSlot


def make_experience(**overrides) -> Experience:
    """Create a minimal public experience for tests."""
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
        "cancellation_hours": 48,
        "is_active": True,
        "is_featured": False,
    }
    defaults.update(overrides)
    return Experience.objects.create(**defaults)


@pytest.mark.django_db
class TestVisitBookingAPI:
    """Coverage for public visit booking and payment flows."""

    @patch("apps.reservations.serializers.MercadoPagoClient.create_booking_preference")
    def test_guest_can_create_booking_and_preference(
        self,
        mock_create_booking_preference,
        api_client,
        settings,
    ) -> None:
        """Public booking should hold slot capacity and return a checkout preference."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=3),
            start_time=timezone.datetime.strptime("11:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("12:30", "%H:%M").time(),
            capacity=10,
            spots_available=10,
        )
        mock_create_booking_preference.return_value = {
            "id": "pref_visit_123",
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref_visit_123",
            "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/v1/redirect?pref_id=pref_visit_123",
        }

        response = api_client.post(
            "/api/v1/visits/bookings/",
            {
                "time_slot": slot.id,
                "guest_count": 4,
                "customer_first_name": "Ana",
                "customer_last_name": "Suarez",
                "customer_email": "ana@example.com",
                "customer_phone": "+5492604000000",
                "special_requests": "Mesa junto a ventana",
                "dietary_restrictions": ["vegetariano"],
            },
            format="json",
        )

        slot.refresh_from_db()
        booking = Booking.objects.get(pk=response.data["booking"]["id"])
        payment = BookingPayment.objects.get(booking=booking)

        assert response.status_code == 201
        assert booking.status == Booking.Status.PENDING_PAYMENT
        assert booking.customer_email == "ana@example.com"
        assert slot.spots_available == 6
        assert payment.mp_preference_id == "pref_visit_123"
        assert response.data["preference"]["guest_access_token"]
        mock_create_booking_preference.assert_called_once()

    @patch("apps.reservations.views.MercadoPagoClient.get_payment")
    def test_booking_webhook_confirms_payment_without_releasing_capacity(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """An approved booking payment should confirm the booking and keep the seat taken."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        experience = make_experience(price_per_person=Decimal("30000.00"))
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
            total_price=Decimal("90000.00"),
            status=Booking.Status.PENDING_PAYMENT,
        )
        payment = BookingPayment.objects.create(
            booking=booking,
            idempotency_key=f"mercadopago:booking:{booking.id}",
            amount=booking.total_price,
            currency="ARS",
            status=BookingPayment.Status.PENDING,
        )
        mock_get_payment.return_value = {
            "id": 99887766,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(booking.id),
            "transaction_amount": "90000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
            "installments": 3,
            "order": {"id": "merchant_order_booking_1"},
        }

        response = api_client.post(
            "/api/v1/visits/payments/webhook/?data.id=99887766&type=payment",
            {"id": 54321, "type": "payment", "data": {"id": "99887766"}},
            format="json",
        )

        booking.refresh_from_db()
        payment.refresh_from_db()
        slot.refresh_from_db()

        assert response.status_code == 200
        assert booking.status == Booking.Status.CONFIRMED
        assert payment.status == BookingPayment.Status.APPROVED
        assert slot.spots_available == 5
        assert PaymentWebhookLog.objects.filter(mp_notification_id="54321").count() == 1

    @patch("apps.reservations.views.MercadoPagoClient.get_payment")
    def test_booking_webhook_releases_capacity_when_payment_fails(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """A rejected payment should release the slot seats again."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=5),
            start_time=timezone.datetime.strptime("16:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("17:00", "%H:%M").time(),
            capacity=10,
            spots_available=7,
        )
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Lucia",
            customer_last_name="Mena",
            customer_email="lucia@example.com",
            customer_phone="+5492604222222",
            guest_count=3,
            total_price=Decimal("75000.00"),
            status=Booking.Status.PENDING_PAYMENT,
        )
        BookingPayment.objects.create(
            booking=booking,
            idempotency_key=f"mercadopago:booking:{booking.id}",
            amount=booking.total_price,
            currency="ARS",
            status=BookingPayment.Status.PENDING,
        )
        mock_get_payment.return_value = {
            "id": 99887767,
            "status": "rejected",
            "status_detail": "cc_rejected_insufficient_amount",
            "external_reference": str(booking.id),
            "transaction_amount": "75000.00",
            "currency_id": "ARS",
            "collector_id": "",
        }

        response = api_client.post(
            "/api/v1/visits/payments/webhook/?data.id=99887767&type=payment",
            {"id": 54322, "type": "payment", "data": {"id": "99887767"}},
            format="json",
        )

        booking.refresh_from_db()
        slot.refresh_from_db()

        assert response.status_code == 200
        assert booking.status == Booking.Status.PAYMENT_FAILED
        assert slot.spots_available == 10

    def test_guest_token_can_read_booking_detail(self, api_client) -> None:
        """Guests should be able to read their booking detail with the signed token."""
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime("10:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("11:30", "%H:%M").time(),
            capacity=6,
            spots_available=4,
        )
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Mora",
            customer_last_name="Funes",
            customer_email="mora@example.com",
            customer_phone="+5492604333333",
            guest_count=2,
            total_price=Decimal("50000.00"),
            status=Booking.Status.CONFIRMED,
        )

        response = api_client.get(
            f"/api/v1/visits/bookings/{booking.id}/?guest_access_token={build_guest_access_token(booking)}"
        )

        assert response.status_code == 200
        assert response.data["confirmation_code"] == booking.confirmation_code
