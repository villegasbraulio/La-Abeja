"""Public serializers for visit booking flows."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import cast

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.authentication.models import CustomUser
from apps.payments.mercadopago import MercadoPagoAPIError, MercadoPagoClient

from .access import build_guest_access_token
from .models import Booking, BookingManualRefund, BookingPayment, Experience, TimeSlot
from .services import (
    booking_holds_capacity,
    expire_pending_booking_holds,
    recalculate_slot_availability,
)


class PublicExperienceSerializer(serializers.ModelSerializer):
    """Serialize active winery experiences for the public booking page."""

    next_available_date = serializers.SerializerMethodField()

    class Meta:
        model = Experience
        fields = [
            "id",
            "name",
            "slug",
            "experience_type",
            "description",
            "duration_minutes",
            "price_per_person",
            "min_guests",
            "max_guests",
            "includes",
            "highlights",
            "cover_image",
            "gallery_images",
            "next_available_date",
        ]

    def get_next_available_date(self, obj: Experience) -> str | None:
        """Expose the next future date with availability."""
        now = timezone.localtime()
        slot = (
            obj.slots.filter(is_blocked=False, spots_available__gt=0, date__gte=now.date())
            .exclude(date=now.date(), start_time__lt=now.time())
            .order_by("date", "start_time")
            .first()
        )
        return slot.date.isoformat() if slot else None


class PublicTimeSlotSerializer(serializers.ModelSerializer):
    """Serialize future bookable slots."""

    experience_name = serializers.CharField(source="experience.name", read_only=True)

    class Meta:
        model = TimeSlot
        fields = [
            "id",
            "experience",
            "experience_name",
            "date",
            "start_time",
            "end_time",
            "capacity",
            "spots_available",
            "guide_name",
        ]


class BookingPaymentSummarySerializer(serializers.ModelSerializer):
    """Serialize the payment snapshot attached to a booking."""

    class Meta:
        model = BookingPayment
        fields = [
            "id",
            "status",
            "status_detail",
            "mp_preference_id",
            "mp_payment_id",
            "amount",
            "payment_method",
            "payment_type",
            "installments",
            "created_at",
            "updated_at",
        ]


class PublicBookingManualRefundSerializer(serializers.ModelSerializer):
    """Serialize customer-safe manual refund state."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BookingManualRefund
        fields = [
            "id",
            "status",
            "status_label",
            "amount",
            "currency",
            "created_at",
            "updated_at",
            "completed_at",
        ]


class PublicBookingSerializer(serializers.ModelSerializer):
    """Serialize bookings returned to the public site."""

    experience_name = serializers.CharField(source="time_slot.experience.name", read_only=True)
    slot_date = serializers.DateField(source="time_slot.date", read_only=True)
    slot_start_time = serializers.TimeField(source="time_slot.start_time", read_only=True)
    slot_end_time = serializers.TimeField(source="time_slot.end_time", read_only=True)
    customer_name = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    guest_access_token = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    manual_refund = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "confirmation_code",
            "customer_name",
            "customer_email",
            "customer_phone",
            "experience_name",
            "slot_date",
            "slot_start_time",
            "slot_end_time",
            "guest_count",
            "total_price",
            "status",
            "status_label",
            "special_requests",
            "dietary_restrictions",
            "hold_expires_at",
            "guest_access_token",
            "payment",
            "manual_refund",
            "created_at",
        ]

    def get_guest_access_token(self, obj: Booking) -> str | None:
        """Return a signed guest token when the booking has no authenticated owner."""
        return build_guest_access_token(obj)

    def get_payment(self, obj: Booking) -> dict[str, object] | None:
        """Return payment details when the booking already has a payment record."""
        try:
            payment = obj.payment
        except BookingPayment.DoesNotExist:
            return None
        return BookingPaymentSummarySerializer(payment).data

    def get_manual_refund(self, obj: Booking) -> dict[str, object] | None:
        """Return manual refund state when staff must process a cancellation."""
        try:
            refund = obj.manual_refund
        except BookingManualRefund.DoesNotExist:
            return None
        return PublicBookingManualRefundSerializer(refund).data


class PublicBookingCreateSerializer(serializers.Serializer):
    """Create a booking and its Mercado Pago preference."""

    time_slot = serializers.IntegerField()
    guest_count = serializers.IntegerField(min_value=1, max_value=50)
    customer_first_name = serializers.CharField(max_length=100)
    customer_last_name = serializers.CharField(max_length=100)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20)
    client_request_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    dietary_restrictions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
    )

    default_error_messages = {
        "slot_unavailable": "Ese horario ya no está disponible.",
        "experience_inactive": "La experiencia seleccionada no admite reservas en este momento.",
        "private_event": "Los eventos privados se coordinan por teléfono o desde contacto.",
    }

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Validate the public booking request against slot availability."""
        slot_id = cast(int, attrs["time_slot"])
        guest_count = cast(int, attrs["guest_count"])
        slot = (
            TimeSlot.objects.select_related("experience")
            .filter(pk=slot_id)
            .first()
        )
        if slot is None:
            raise serializers.ValidationError(
                {"time_slot": self.error_messages["slot_unavailable"]}
            )
        if slot.experience.experience_type == Experience.ExperienceType.PRIVATE_EVENT:
            raise serializers.ValidationError({"time_slot": self.error_messages["private_event"]})
        if not slot.experience.is_active or slot.is_blocked:
            raise serializers.ValidationError(
                {"time_slot": self.error_messages["experience_inactive"]}
            )

        now = timezone.localtime()
        if slot.date < now.date() or (slot.date == now.date() and slot.start_time < now.time()):
            raise serializers.ValidationError(
                {"time_slot": self.error_messages["slot_unavailable"]}
            )

        if guest_count < slot.experience.min_guests or guest_count > slot.experience.max_guests:
            raise serializers.ValidationError(
                {
                    "guest_count": (
                        f"Esta visita admite entre {slot.experience.min_guests} y "
                        f"{slot.experience.max_guests} personas."
                    )
                }
            )

        attrs["slot_instance"] = slot
        return attrs

    def create_with_preference(self) -> dict[str, object]:
        """Create the booking and return it together with the checkout preference."""
        expire_pending_booking_holds()
        booking, payment = self._create_pending_booking()
        if not payment.mp_preference_id:
            try:
                preference = MercadoPagoClient().create_booking_preference(
                    booking,
                    idempotency_key=payment.idempotency_key,
                )
            except MercadoPagoAPIError:
                self._mark_payment_attempt_failed(payment_id=payment.id)
                raise

            payment.mp_preference_id = str(preference["id"])
            payment.preference_init_point = str(preference.get("init_point") or "")
            payment.preference_sandbox_init_point = str(preference.get("sandbox_init_point") or "")
            payment.status = BookingPayment.Status.PENDING
            payment.amount = booking.total_price
            payment.currency = "ARS"
            payment.save(
                update_fields=[
                    "mp_preference_id",
                    "preference_init_point",
                    "preference_sandbox_init_point",
                    "status",
                    "amount",
                    "currency",
                    "updated_at",
                ]
            )
        return {
            "booking": booking,
            "preference": {
                "booking_id": str(booking.id),
                "confirmation_code": booking.confirmation_code,
                "preference_id": payment.mp_preference_id,
                "init_point": payment.preference_init_point or None,
                "sandbox_init_point": payment.preference_sandbox_init_point or None,
                "hold_expires_at": booking.hold_expires_at.isoformat()
                if booking.hold_expires_at
                else None,
                "hold_minutes": settings.BOOKING_HOLD_MINUTES,
                "guest_access_token": build_guest_access_token(booking),
            },
        }

    @transaction.atomic
    def _create_pending_booking(self) -> tuple[Booking, BookingPayment]:
        """Persist a pending booking while locking the slot capacity."""
        request = self.context["request"]
        validated_data = self.validated_data
        client_request_id = str(validated_data.get("client_request_id") or "").strip()
        if client_request_id:
            existing_booking = (
                Booking.objects.select_for_update()
                .select_related("time_slot", "time_slot__experience")
                .filter(client_request_id=client_request_id)
                .first()
            )
            if existing_booking is not None:
                if not booking_holds_capacity(existing_booking):
                    raise serializers.ValidationError(
                        {"client_request_id": "Ese intento de reserva venció. Iniciá uno nuevo."}
                    )
                return existing_booking, existing_booking.payment

        slot = TimeSlot.objects.select_for_update().select_related("experience").get(
            pk=validated_data["time_slot"]
        )
        guest_count = cast(int, validated_data["guest_count"])

        if slot.experience_id != cast(TimeSlot, validated_data["slot_instance"]).experience_id:
            raise serializers.ValidationError(
                {"time_slot": self.error_messages["slot_unavailable"]}
            )

        current_available = recalculate_slot_availability(slot)
        if guest_count > current_available:
            raise serializers.ValidationError(
                {
                    "guest_count": (
                        f"Solo quedan {current_available} lugares disponibles para ese horario."
                    )
                }
            )

        user = request.user if request.user.is_authenticated else None
        hold_expires_at = timezone.now() + timedelta(minutes=settings.BOOKING_HOLD_MINUTES)
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            user=cast(CustomUser | None, user),
            time_slot=slot,
            customer_first_name=str(validated_data["customer_first_name"]).strip(),
            customer_last_name=str(validated_data["customer_last_name"]).strip(),
            customer_email=str(validated_data["customer_email"]).strip().lower(),
            customer_phone=str(validated_data["customer_phone"]).strip(),
            guest_count=guest_count,
            total_price=Decimal(slot.experience.price_per_person) * guest_count,
            status=Booking.Status.PENDING_PAYMENT,
            special_requests=str(validated_data.get("special_requests") or "").strip(),
            dietary_restrictions=validated_data.get("dietary_restrictions") or [],
            hold_expires_at=hold_expires_at,
            client_request_id=client_request_id,
        )
        recalculate_slot_availability(slot)

        payment = BookingPayment.objects.create(
            booking=booking,
            idempotency_key=f"mercadopago:booking:{booking.id}",
            status=BookingPayment.Status.PENDING,
            amount=booking.total_price,
            currency="ARS",
        )
        return booking, payment

    @transaction.atomic
    def _mark_payment_attempt_failed(self, *, payment_id) -> None:
        """Release the held slot when preference creation fails."""
        payment = (
            BookingPayment.objects.select_for_update()
            .select_related("booking", "booking__time_slot")
            .get(pk=payment_id)
        )
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        slot = TimeSlot.objects.select_for_update().get(pk=booking.time_slot_id)
        payment.status = BookingPayment.Status.REJECTED
        payment.status_detail = "preference_creation_failed"
        payment.save(update_fields=["status", "status_detail", "updated_at"])
        if booking_holds_capacity(booking):
            booking.status = Booking.Status.PAYMENT_FAILED
            booking.hold_expires_at = None
            booking.save(update_fields=["status", "hold_expires_at"])
            recalculate_slot_availability(slot)
