"""Administration for durable automation events."""

from django.contrib import admin

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    """Operational view of pending and failed side effects."""

    list_display = ("event_type", "event_key", "status", "attempts", "available_at")
    list_filter = ("event_type", "status", "created_at")
    search_fields = ("event_key", "last_error")
    readonly_fields = (
        "event_key",
        "event_type",
        "payload",
        "status",
        "attempts",
        "available_at",
        "processed_at",
        "last_error",
        "created_at",
        "updated_at",
    )
