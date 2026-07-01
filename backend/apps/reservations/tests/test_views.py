"""Public visit booking API coverage."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.automations.models import OutboxEvent
from apps.payments.models import PaymentWebhookLog
from apps.reservations.access import build_guest_access_token
from apps.reservations.models import (
    Booking,
    BookingManualRefund,
    BookingPayment,
    Experience,
    TimeSlot,
)


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
        "cancellation_hours": 24,
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
        assert booking.hold_expires_at is not None
        assert slot.spots_available == 6
        assert payment.mp_preference_id == "pref_visit_123"
        assert response.data["preference"]["hold_minutes"] == 15
        assert response.data["preference"]["hold_expires_at"]
        assert response.data["preference"]["guest_access_token"]
        mock_create_booking_preference.assert_called_once()

    @patch("apps.reservations.serializers.MercadoPagoClient.create_booking_preference")
    def test_booking_create_is_idempotent_for_same_client_request(
        self,
        mock_create_booking_preference,
        api_client,
        settings,
    ) -> None:
        """Retrying the same public booking request should reuse the first booking."""
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
            "id": "pref_visit_idem",
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref_visit_idem",
            "sandbox_init_point": "",
        }
        payload = {
            "time_slot": slot.id,
            "guest_count": 2,
            "customer_first_name": "Ana",
            "customer_last_name": "Suarez",
            "customer_email": "ana@example.com",
            "customer_phone": "+5492604000000",
            "client_request_id": "visit-request-123",
        }

        first_response = api_client.post("/api/v1/visits/bookings/", payload, format="json")
        second_response = api_client.post("/api/v1/visits/bookings/", payload, format="json")

        slot.refresh_from_db()
        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert first_response.data["booking"]["id"] == second_response.data["booking"]["id"]
        assert Booking.objects.filter(client_request_id="visit-request-123").count() == 1
        assert slot.spots_available == 8
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
        assert OutboxEvent.objects.filter(
            event_key=f"booking-email:{booking.id}:confirmed",
            event_type=OutboxEvent.EventType.BOOKING_EMAIL,
        ).exists()
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

    @patch("apps.reservations.views.MercadoPagoClient.get_payment")
    def test_late_approved_payment_does_not_overbook_expired_hold(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """An approved payment after an expired hold must not displace confirmed guests."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        experience = make_experience(price_per_person=Decimal("30000.00"), max_guests=6)
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=2),
            start_time=timezone.datetime.strptime("13:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("14:30", "%H:%M").time(),
            capacity=3,
            spots_available=0,
        )
        expired_booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Juan",
            customer_last_name="Paz",
            customer_email="juan@example.com",
            customer_phone="+5492604111111",
            guest_count=3,
            total_price=Decimal("90000.00"),
            status=Booking.Status.PENDING_PAYMENT,
            hold_expires_at=timezone.now() - timedelta(minutes=5),
        )
        BookingPayment.objects.create(
            booking=expired_booking,
            idempotency_key=f"mercadopago:booking:{expired_booking.id}",
            amount=expired_booking.total_price,
            currency="ARS",
            status=BookingPayment.Status.PENDING,
        )
        Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Mora",
            customer_last_name="Funes",
            customer_email="mora@example.com",
            customer_phone="+5492604333333",
            guest_count=3,
            total_price=Decimal("90000.00"),
            status=Booking.Status.CONFIRMED,
        )
        mock_get_payment.return_value = {
            "id": 99887768,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(expired_booking.id),
            "transaction_amount": "90000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
        }

        response = api_client.post(
            "/api/v1/visits/payments/webhook/?data.id=99887768&type=payment",
            {"id": 54323, "type": "payment", "data": {"id": "99887768"}},
            format="json",
        )

        expired_booking.refresh_from_db()
        expired_booking.payment.refresh_from_db()
        slot.refresh_from_db()
        assert response.status_code == 200
        assert expired_booking.status == Booking.Status.PAYMENT_FAILED
        assert expired_booking.payment.status == BookingPayment.Status.APPROVED
        assert expired_booking.payment.status_detail == "capacity_unavailable_after_payment"
        assert slot.spots_available == 0

    def test_private_events_are_not_publicly_bookable(self, api_client) -> None:
        """Private events should stay in the contact/manual channel."""
        experience = make_experience(
            slug="evento-privado-test",
            experience_type=Experience.ExperienceType.PRIVATE_EVENT,
        )
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=3),
            start_time=timezone.datetime.strptime("19:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("22:00", "%H:%M").time(),
            capacity=20,
            spots_available=20,
        )

        list_response = api_client.get("/api/v1/visits/experiences/")
        create_response = api_client.post(
            "/api/v1/visits/bookings/",
            {
                "time_slot": slot.id,
                "guest_count": 10,
                "customer_first_name": "Ana",
                "customer_last_name": "Suarez",
                "customer_email": "ana@example.com",
                "customer_phone": "+5492604000000",
            },
            format="json",
        )

        assert list_response.status_code == 200
        assert all(item["id"] != str(experience.id) for item in list_response.data)
        assert create_response.status_code == 400
        assert "teléfono" in create_response.data["time_slot"][0]

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
        assert "hold_expires_at" in response.data

    def test_guest_can_cancel_confirmed_booking_and_create_manual_refund(
        self,
        api_client,
    ) -> None:
        """Customer cancellation should release seats and register the manual refund task."""
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=3),
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
        payment = BookingPayment.objects.create(
            booking=booking,
            idempotency_key=f"mercadopago:booking:{booking.id}",
            amount=booking.total_price,
            currency="ARS",
            status=BookingPayment.Status.APPROVED,
        )

        response = api_client.post(
            (
                f"/api/v1/visits/bookings/{booking.id}/cancel/"
                f"?guest_access_token={build_guest_access_token(booking)}"
            ),
            format="json",
        )

        booking.refresh_from_db()
        payment.refresh_from_db()
        slot.refresh_from_db()
        refund = BookingManualRefund.objects.get(booking=booking)
        assert response.status_code == 200
        assert booking.status == Booking.Status.CANCELLED
        assert payment.status == BookingPayment.Status.APPROVED
        assert slot.spots_available == 6
        assert refund.status == BookingManualRefund.Status.PENDING
        assert refund.amount == Decimal("50000.00")
        assert refund.operator is None
        assert response.data["manual_refund"]["status"] == BookingManualRefund.Status.PENDING

    def test_guest_cannot_cancel_inside_24h_window(self, api_client) -> None:
        """Customer cancellation should respect the experience cancellation window."""
        experience = make_experience()
        soon = timezone.localtime() + timedelta(hours=12)
        slot = TimeSlot.objects.create(
            experience=experience,
            date=soon.date(),
            start_time=soon.time(),
            end_time=(soon + timedelta(hours=1)).time(),
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

        response = api_client.post(
            (
                f"/api/v1/visits/bookings/{booking.id}/cancel/"
                f"?guest_access_token={build_guest_access_token(booking)}"
            ),
            format="json",
        )

        booking.refresh_from_db()
        slot.refresh_from_db()
        assert response.status_code == 400
        assert booking.status == Booking.Status.CONFIRMED
        assert slot.spots_available == 4

    def test_staff_can_create_manual_booking(self, authenticated_client) -> None:
        """Backoffice staff should be able to create confirmed manual reservations."""
        client, user = authenticated_client
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=4),
            start_time=timezone.datetime.strptime("12:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("13:30", "%H:%M").time(),
            capacity=8,
            spots_available=8,
        )

        response = client.post(
            "/api/v1/backoffice/visits/bookings/",
            {
                "time_slot": slot.id,
                "guest_count": 3,
                "customer_first_name": "Mora",
                "customer_last_name": "Funes",
                "customer_email_input": "mora@example.com",
                "customer_phone_input": "+5492604333333",
                "special_requests": "Reserva tomada por teléfono",
            },
            format="json",
        )

        slot.refresh_from_db()
        booking = Booking.objects.get(pk=response.data["id"])
        assert response.status_code == 201
        assert booking.status == Booking.Status.CONFIRMED
        assert booking.total_price == Decimal("75000.00")
        assert slot.spots_available == 5
        assert not hasattr(booking, "payment")

    def test_staff_can_view_reservation_metrics(self, authenticated_client) -> None:
        """Backoffice staff should see visit revenue, occupancy, and status KPIs."""
        client, user = authenticated_client
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        experience = make_experience(name="Cata de Barricas")
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate(),
            start_time=timezone.datetime.strptime("12:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("13:30", "%H:%M").time(),
            capacity=8,
            spots_available=5,
        )
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Mora",
            customer_last_name="Funes",
            customer_email="mora@example.com",
            customer_phone="+5492604333333",
            guest_count=3,
            total_price=Decimal("75000.00"),
            status=Booking.Status.CONFIRMED,
            special_requests="Mesa cerca de la galeria.",
            dietary_restrictions=["sin gluten"],
        )
        BookingManualRefund.objects.create(
            booking=booking,
            amount=Decimal("25000.00"),
            status=BookingManualRefund.Status.PENDING,
        )

        response = client.get("/api/v1/backoffice/visits/reservation-metrics/?period=last_30_days")

        assert response.status_code == 200
        assert response.data["summary"]["booking_count"] == 1
        assert response.data["summary"]["total_revenue"] == "75000"
        assert response.data["capacity"]["booked_guests"] == 3
        assert response.data["capacity"]["occupancy_rate"] == 0.375
        assert response.data["by_experience"]["results"][0]["experience_name"] == "Cata de Barricas"
        assert response.data["operations"]["pending_refunds_count"] == 1
        assert response.data["operations"]["dietary_restrictions_count"] == 1

    def test_staff_can_move_manual_booking_between_slots(self, authenticated_client) -> None:
        """Moving a manual booking should release the origin slot and occupy the new one."""
        client, user = authenticated_client
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        experience = make_experience()
        first_slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=4),
            start_time=timezone.datetime.strptime("12:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("13:30", "%H:%M").time(),
            capacity=8,
            spots_available=5,
        )
        second_slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=5),
            start_time=timezone.datetime.strptime("15:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("16:30", "%H:%M").time(),
            capacity=8,
            spots_available=8,
        )
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=first_slot,
            customer_first_name="Mora",
            customer_last_name="Funes",
            customer_email="mora@example.com",
            customer_phone="+5492604333333",
            guest_count=3,
            total_price=Decimal("75000.00"),
            status=Booking.Status.CONFIRMED,
        )

        response = client.patch(
            f"/api/v1/backoffice/visits/bookings/{booking.id}/",
            {"time_slot": second_slot.id},
            format="json",
        )

        booking.refresh_from_db()
        first_slot.refresh_from_db()
        second_slot.refresh_from_db()
        assert response.status_code == 200
        assert booking.time_slot_id == second_slot.id
        assert first_slot.spots_available == 8
        assert second_slot.spots_available == 5

    def test_staff_cancellation_creates_and_updates_manual_refund(
        self,
        authenticated_client,
    ) -> None:
        """Backoffice cancellation should track the manual refund with operator notes."""
        client, user = authenticated_client
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        experience = make_experience()
        slot = TimeSlot.objects.create(
            experience=experience,
            date=timezone.localdate() + timedelta(days=4),
            start_time=timezone.datetime.strptime("12:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("13:30", "%H:%M").time(),
            capacity=8,
            spots_available=5,
        )
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name="Mora",
            customer_last_name="Funes",
            customer_email="mora@example.com",
            customer_phone="+5492604333333",
            guest_count=3,
            total_price=Decimal("75000.00"),
            status=Booking.Status.CONFIRMED,
        )
        BookingPayment.objects.create(
            booking=booking,
            idempotency_key=f"mercadopago:booking:{booking.id}",
            amount=booking.total_price,
            currency="ARS",
            status=BookingPayment.Status.APPROVED,
        )

        cancel_response = client.patch(
            f"/api/v1/backoffice/visits/bookings/{booking.id}/",
            {
                "status": Booking.Status.CANCELLED,
                "guest_count": 3,
                "special_requests": "",
                "checked_in_at": None,
                "manual_refund_note": "Cliente pidió cancelar por teléfono.",
            },
            format="json",
        )
        complete_response = client.patch(
            f"/api/v1/backoffice/visits/bookings/{booking.id}/",
            {
                "status": Booking.Status.CANCELLED,
                "guest_count": 3,
                "special_requests": "",
                "checked_in_at": None,
                "manual_refund_status": BookingManualRefund.Status.COMPLETED,
                "manual_refund_note": "Reintegro hecho manualmente.",
            },
            format="json",
        )

        booking.refresh_from_db()
        slot.refresh_from_db()
        refund = BookingManualRefund.objects.get(booking=booking)
        assert cancel_response.status_code == 200
        assert complete_response.status_code == 200
        assert booking.status == Booking.Status.CANCELLED
        assert slot.spots_available == 8
        assert refund.status == BookingManualRefund.Status.COMPLETED
        assert refund.note == "Reintegro hecho manualmente."
        assert refund.operator_id == user.id
        assert refund.completed_at is not None
        assert complete_response.data["manual_refund"]["status"] == "completed"
