"""Admin registrations for reservations models."""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, BookingManualRefund, BookingPayment, Experience, TimeSlot


class TimeSlotInline(admin.TabularInline):
    """Inline time slot editor for visit experiences."""

    model = TimeSlot
    extra = 1
    fields = (
        "date",
        "start_time",
        "end_time",
        "capacity",
        "spots_available",
        "guide_name",
        "is_blocked",
        "block_reason",
    )


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    """Backoffice-friendly admin for visit experiences."""

    inlines = [TimeSlotInline]
    list_display = (
        "name",
        "experience_type",
        "duration_minutes",
        "price_per_person",
        "is_active",
        "is_featured",
        "cover_preview",
    )
    list_filter = ("experience_type", "is_active", "is_featured")
    search_fields = ("name", "slug", "description")
    ordering = ("-is_featured", "name")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Portada")
    def cover_preview(self, obj: Experience) -> str:
        """Render a compact preview for the cover image URL."""
        if not obj.cover_image:
            return "Sin imagen"
        return format_html(
            (
                '<img src="{}" alt="{}" '
                'style="width: 64px; height: 64px; object-fit: cover; border-radius: 14px;" />'
            ),
            obj.cover_image,
            obj.name,
        )


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """Admin for slot scheduling."""

    list_display = (
        "experience",
        "date",
        "start_time",
        "end_time",
        "capacity",
        "spots_available",
        "is_blocked",
    )
    list_filter = ("experience", "date", "is_blocked")
    search_fields = ("experience__name", "guide_name", "block_reason")
    ordering = ("-date", "start_time")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Admin for visit bookings."""

    list_display = (
        "confirmation_code",
        "user",
        "experience",
        "slot_date",
        "guest_count",
        "status",
        "checked_in_at",
    )
    list_filter = ("status", "time_slot__experience", "time_slot__date")
    search_fields = (
        "confirmation_code",
        "user__email",
        "user__first_name",
        "user__last_name",
        "time_slot__experience__name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    @admin.display(description="Experiencia")
    def experience(self, obj: Booking) -> str:
        """Return the associated experience name."""
        return obj.time_slot.experience.name

    @admin.display(description="Fecha")
    def slot_date(self, obj: Booking) -> str:
        """Return the date of the booked slot."""
        return str(obj.time_slot.date)


@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    """Admin for Mercado Pago visit payments."""

    list_display = (
        "booking",
        "status",
        "amount",
        "currency",
        "mp_payment_id",
        "updated_at",
    )
    list_filter = ("status", "currency")
    search_fields = (
        "booking__confirmation_code",
        "booking__customer_email",
        "mp_preference_id",
        "mp_payment_id",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(BookingManualRefund)
class BookingManualRefundAdmin(admin.ModelAdmin):
    """Admin for manual visit refund tracking."""

    list_display = (
        "booking",
        "status",
        "amount",
        "currency",
        "operator",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "currency")
    search_fields = (
        "booking__confirmation_code",
        "booking__customer_email",
        "operator__email",
        "note",
    )
    readonly_fields = ("created_at", "updated_at")
