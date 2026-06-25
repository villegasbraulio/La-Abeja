"""Serializers for the reservations backoffice API."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.template.defaultfilters import slugify
from rest_framework import serializers

from apps.authentication.models import CustomUser

from .models import Booking, BookingManualRefund, Experience, TimeSlot
from .services import (
    ReservationCapacityError,
    booking_holds_capacity,
    cancel_booking,
    ensure_manual_refund_record,
    mark_manual_refund,
    recalculate_slot_availability,
)


class BackofficeExperienceSerializer(serializers.ModelSerializer):
    """Serialize bookable experiences for the backoffice."""

    bookings_count = serializers.IntegerField(read_only=True)
    slots_count = serializers.IntegerField(read_only=True)

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
            "cancellation_hours",
            "is_active",
            "is_featured",
            "bookings_count",
            "slots_count",
        ]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Generate a slug automatically when the operator leaves it blank."""
        name = str(attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = str(attrs.get("slug") or "").strip()
        if name and not slug:
            attrs["slug"] = slugify(name)
        return attrs


class BackofficeTimeSlotSerializer(serializers.ModelSerializer):
    """Serialize slot data for visit planning."""

    experience_name = serializers.CharField(source="experience.name", read_only=True)
    booked_guests = serializers.SerializerMethodField()

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
            "booked_guests",
            "guide_name",
            "is_blocked",
            "block_reason",
        ]
        read_only_fields = ["spots_available", "booked_guests"]

    def get_booked_guests(self, obj: TimeSlot) -> int:
        """Expose the current seat consumption for the slot."""
        return max(obj.capacity - obj.spots_available, 0)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Keep the slot timing and capacity internally consistent."""
        start_time = attrs.get("start_time") or getattr(self.instance, "start_time", None)
        end_time = attrs.get("end_time") or getattr(self.instance, "end_time", None)
        capacity = attrs.get("capacity")

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                {"end_time": "La hora de fin debe ser posterior a la hora de inicio."}
            )

        if self.instance and capacity is not None:
            current_capacity = int(capacity)
            reserved = self.instance.capacity - self.instance.spots_available
            if current_capacity < reserved:
                raise serializers.ValidationError(
                    {
                        "capacity": (
                            "La capacidad no puede quedar por debajo de las reservas activas "
                            f"({reserved})."
                        )
                    }
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, object]) -> TimeSlot:
        """Create a slot and initialize its availability from capacity."""
        slot = TimeSlot.objects.create(
            **validated_data,
            spots_available=int(validated_data["capacity"]),
        )
        recalculate_slot_availability(slot)
        return slot

    @transaction.atomic
    def update(self, instance: TimeSlot, validated_data: dict[str, object]) -> TimeSlot:
        """Update a slot and recompute its derived availability."""
        slot = TimeSlot.objects.select_for_update().get(pk=instance.pk)
        for field, value in validated_data.items():
            setattr(slot, field, value)
        slot.save()
        try:
            recalculate_slot_availability(slot)
        except ReservationCapacityError as exc:
            raise serializers.ValidationError({"capacity": str(exc)}) from exc
        return slot


class BackofficeBookingSerializer(serializers.ModelSerializer):
    """Serialize customer bookings for the backoffice."""

    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    time_slot = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.select_related("experience").all(),
        required=False,
        write_only=True,
    )
    customer_first_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        write_only=True,
    )
    customer_last_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        write_only=True,
    )
    customer_email_input = serializers.EmailField(
        source="customer_email",
        required=False,
        allow_blank=True,
        write_only=True,
    )
    customer_phone_input = serializers.CharField(
        source="customer_phone",
        max_length=20,
        required=False,
        allow_blank=True,
        write_only=True,
    )
    experience_name = serializers.CharField(source="time_slot.experience.name", read_only=True)
    experience_type = serializers.CharField(
        source="time_slot.experience.experience_type",
        read_only=True,
    )
    slot_date = serializers.DateField(source="time_slot.date", read_only=True)
    slot_start_time = serializers.TimeField(source="time_slot.start_time", read_only=True)
    slot_end_time = serializers.TimeField(source="time_slot.end_time", read_only=True)
    payment_status = serializers.CharField(source="payment.status", read_only=True)
    payment_status_detail = serializers.CharField(source="payment.status_detail", read_only=True)
    manual_refund = serializers.SerializerMethodField()
    manual_refund_status = serializers.ChoiceField(
        choices=BookingManualRefund.Status.choices,
        required=False,
        write_only=True,
    )
    manual_refund_note = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "confirmation_code",
            "time_slot",
            "customer_name",
            "customer_email",
            "customer_phone",
            "customer_first_name",
            "customer_last_name",
            "customer_email_input",
            "customer_phone_input",
            "experience_name",
            "experience_type",
            "slot_date",
            "slot_start_time",
            "slot_end_time",
            "guest_count",
            "total_price",
            "status",
            "special_requests",
            "dietary_restrictions",
            "qr_code_url",
            "checked_in_at",
            "payment_status",
            "payment_status_detail",
            "manual_refund",
            "manual_refund_status",
            "manual_refund_note",
            "reminder_24h_sent",
            "reminder_1h_sent",
            "hold_expires_at",
            "created_at",
        ]
        read_only_fields = [
            "confirmation_code",
            "total_price",
            "payment_status",
            "payment_status_detail",
            "reminder_24h_sent",
            "reminder_1h_sent",
            "hold_expires_at",
            "created_at",
        ]

    def get_customer_name(self, obj: Booking) -> str:
        """Return a friendly customer name for staff."""
        if obj.user_id and obj.user:
            user: CustomUser = obj.user
            name = f"{user.first_name} {user.last_name}".strip()
            if name:
                return name
            if user.email:
                return user.email
        return obj.customer_name

    def get_customer_email(self, obj: Booking) -> str:
        """Return the best available customer email."""
        if obj.user_id and obj.user and obj.user.email:
            return obj.user.email
        return obj.customer_email

    def get_customer_phone(self, obj: Booking) -> str:
        """Return the best available customer phone."""
        if obj.user_id and obj.user and obj.user.phone:
            return obj.user.phone
        return obj.customer_phone

    def get_manual_refund(self, obj: Booking) -> dict[str, object] | None:
        """Return the staff-facing refund record when one exists."""
        try:
            refund = obj.manual_refund
        except BookingManualRefund.DoesNotExist:
            return None
        operator = refund.operator
        return {
            "id": str(refund.id),
            "status": refund.status,
            "status_label": refund.get_status_display(),
            "amount": str(refund.amount),
            "currency": refund.currency,
            "reason": refund.reason,
            "note": refund.note,
            "operator": str(operator.id) if operator else None,
            "operator_email": operator.email if operator else "",
            "created_at": refund.created_at,
            "updated_at": refund.updated_at,
            "completed_at": refund.completed_at,
        }

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Validate manual booking changes against the selected slot."""
        slot = attrs.get("time_slot") or getattr(self.instance, "time_slot", None)
        if self.instance is None and slot is None:
            raise serializers.ValidationError(
                {"time_slot": "Seleccioná un turno para la reserva manual."}
            )
        if slot is None:
            return attrs

        guest_count = int(attrs.get("guest_count") or getattr(self.instance, "guest_count", 0) or 0)
        if guest_count < slot.experience.min_guests or guest_count > slot.experience.max_guests:
            raise serializers.ValidationError(
                {
                    "guest_count": (
                        f"Esta visita admite entre {slot.experience.min_guests} y "
                        f"{slot.experience.max_guests} personas."
                    )
                }
            )
        is_assigning_slot = self.instance is None or "time_slot" in attrs
        if slot.is_blocked and is_assigning_slot:
            raise serializers.ValidationError(
                {"time_slot": "No se puede reservar un turno bloqueado."}
            )
        if self.instance is None and "status" not in attrs:
            attrs["status"] = Booking.Status.CONFIRMED
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, object]) -> Booking:
        """Create a manual booking from the backoffice."""
        slot_ref = validated_data.pop("time_slot")
        slot = TimeSlot.objects.select_for_update().select_related("experience").get(pk=slot_ref.pk)
        guest_count = int(validated_data["guest_count"])
        booking = Booking.objects.create(
            confirmation_code=Booking.generate_confirmation_code(),
            time_slot=slot,
            customer_first_name=str(validated_data.get("customer_first_name") or "").strip(),
            customer_last_name=str(validated_data.get("customer_last_name") or "").strip(),
            customer_email=str(validated_data.get("customer_email") or "").strip().lower(),
            customer_phone=str(validated_data.get("customer_phone") or "").strip(),
            guest_count=guest_count,
            total_price=Decimal(slot.experience.price_per_person) * guest_count,
            status=str(validated_data.get("status") or Booking.Status.CONFIRMED),
            special_requests=str(validated_data.get("special_requests") or "").strip(),
            dietary_restrictions=validated_data.get("dietary_restrictions") or [],
            checked_in_at=validated_data.get("checked_in_at"),
        )
        try:
            recalculate_slot_availability(slot)
        except ReservationCapacityError as exc:
            raise serializers.ValidationError({"guest_count": str(exc)}) from exc
        return booking

    @transaction.atomic
    def update(self, instance: Booking, validated_data: dict[str, object]) -> Booking:
        """Update a booking and keep slot availability consistent."""
        refund_status = validated_data.pop("manual_refund_status", None)
        refund_note = validated_data.pop("manual_refund_note", None)
        request = self.context.get("request")
        operator = request.user if request is not None else None
        booking = Booking.objects.select_for_update().get(pk=instance.pk)
        old_slot_id = booking.time_slot_id
        new_slot_ref = validated_data.get("time_slot")
        slot_id = new_slot_ref.pk if isinstance(new_slot_ref, TimeSlot) else old_slot_id
        slot = (
            TimeSlot.objects.select_for_update()
            .select_related("experience")
            .get(pk=slot_id)
        )
        for field, value in validated_data.items():
            if field == "time_slot":
                booking.time_slot = slot
            else:
                setattr(booking, field, value)
        if "guest_count" in validated_data or new_slot_ref is not None:
            booking.total_price = Decimal(slot.experience.price_per_person) * int(
                booking.guest_count
            )
        if not booking_holds_capacity(booking):
            booking.hold_expires_at = None
        booking.save()
        refund = None
        if booking.status == Booking.Status.CANCELLED:
            booking, refund = cancel_booking(
                booking,
                actor=operator,
                note=str(refund_note or "").strip(),
                enforce_deadline=False,
            )
        elif refund_note is not None or refund_status is not None:
            refund = ensure_manual_refund_record(
                booking,
                operator=operator,
                note=str(refund_note or "").strip(),
            )
            if refund is None:
                raise serializers.ValidationError(
                    {
                        "manual_refund_status": (
                            "No hay un pago aprobado que requiera reembolso manual."
                        )
                    }
                )
        if refund is not None and (refund_note is not None or refund_status is not None):
            mark_manual_refund(
                refund,
                status=str(refund_status) if refund_status is not None else None,
                note=str(refund_note) if refund_note is not None else None,
                operator=operator,
            )
        try:
            for affected_slot in TimeSlot.objects.select_for_update().filter(
                pk__in={old_slot_id, slot.id}
            ):
                recalculate_slot_availability(affected_slot)
        except ReservationCapacityError as exc:
            raise serializers.ValidationError({"guest_count": str(exc)}) from exc
        return booking
