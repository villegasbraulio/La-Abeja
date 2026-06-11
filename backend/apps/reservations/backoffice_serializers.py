"""Serializers for the reservations backoffice API."""

from __future__ import annotations

from django.template.defaultfilters import slugify
from rest_framework import serializers

from apps.authentication.models import CustomUser

from .models import Booking, Experience, TimeSlot


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
            "is_blocked",
            "block_reason",
        ]


class BackofficeBookingSerializer(serializers.ModelSerializer):
    """Serialize customer bookings for the backoffice."""

    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    experience_name = serializers.CharField(source="time_slot.experience.name", read_only=True)
    experience_type = serializers.CharField(source="time_slot.experience.experience_type", read_only=True)
    slot_date = serializers.DateField(source="time_slot.date", read_only=True)
    slot_start_time = serializers.TimeField(source="time_slot.start_time", read_only=True)
    slot_end_time = serializers.TimeField(source="time_slot.end_time", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "confirmation_code",
            "customer_name",
            "customer_email",
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
            "reminder_24h_sent",
            "reminder_1h_sent",
            "created_at",
        ]

    def get_customer_name(self, obj: Booking) -> str:
        """Return a friendly customer name for staff."""
        user: CustomUser = obj.user
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email

