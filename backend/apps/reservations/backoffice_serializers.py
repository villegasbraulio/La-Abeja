"""Serializers for the reservations backoffice API."""

from __future__ import annotations

from django.db import transaction
from django.template.defaultfilters import slugify
from rest_framework import serializers

from apps.authentication.models import CustomUser

from .models import Booking, Experience, TimeSlot
from .services import ReservationCapacityError, recalculate_slot_availability


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
    experience_name = serializers.CharField(source="time_slot.experience.name", read_only=True)
    experience_type = serializers.CharField(source="time_slot.experience.experience_type", read_only=True)
    slot_date = serializers.DateField(source="time_slot.date", read_only=True)
    slot_start_time = serializers.TimeField(source="time_slot.start_time", read_only=True)
    slot_end_time = serializers.TimeField(source="time_slot.end_time", read_only=True)
    payment_status = serializers.CharField(source="payment.status", read_only=True)
    payment_status_detail = serializers.CharField(source="payment.status_detail", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "confirmation_code",
            "customer_name",
            "customer_email",
            "customer_phone",
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
            "reminder_24h_sent",
            "reminder_1h_sent",
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

    @transaction.atomic
    def update(self, instance: Booking, validated_data: dict[str, object]) -> Booking:
        """Update a booking and keep slot availability consistent."""
        booking = Booking.objects.select_for_update().get(pk=instance.pk)
        slot = TimeSlot.objects.select_for_update().get(pk=booking.time_slot_id)
        for field, value in validated_data.items():
            setattr(booking, field, value)
        booking.save()
        try:
            recalculate_slot_availability(slot)
        except ReservationCapacityError as exc:
            raise serializers.ValidationError({"guest_count": str(exc)}) from exc
        return booking
