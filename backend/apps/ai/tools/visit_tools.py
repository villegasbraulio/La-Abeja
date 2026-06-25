"""Visit and event consultation tools."""

from __future__ import annotations

from django.db.models import Count, Q

from apps.reservations.models import Booking, Experience, TimeSlot

from .base import ToolContext


def search_visit_context(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search experiences, slots, and bookings related to visits and events."""
    if not context.is_staff:
        return {"error": "staff_required", "experiences": [], "slots": [], "bookings": []}

    query = str(payload.get("query") or "").strip()
    status = str(payload.get("status") or "").strip()
    experience_id = str(payload.get("experience_id") or "").strip()
    limit = _payload_limit(payload, default=5)

    experiences_qs = Experience.objects.annotate(
        bookings_count=Count("slots__bookings", distinct=True),
        slots_count=Count("slots", distinct=True),
    ).order_by("-is_featured", "name")
    if query:
        experiences_qs = experiences_qs.filter(
            Q(name__icontains=query)
            | Q(slug__icontains=query)
            | Q(description__icontains=query)
            | Q(experience_type__icontains=query)
        )
    if experience_id:
        experiences_qs = experiences_qs.filter(id=experience_id)

    bookings_qs = (
        Booking.objects.select_related("user", "time_slot", "time_slot__experience")
        .order_by("-created_at")
    )
    if query:
        bookings_qs = bookings_qs.filter(
            Q(confirmation_code__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(time_slot__experience__name__icontains=query)
            | Q(time_slot__experience__slug__icontains=query)
            | Q(special_requests__icontains=query)
        )
    if status:
        bookings_qs = bookings_qs.filter(status=status)
    if experience_id:
        bookings_qs = bookings_qs.filter(time_slot__experience_id=experience_id)

    slots_qs = TimeSlot.objects.select_related("experience").order_by("-date", "start_time")
    if query:
        slots_qs = slots_qs.filter(
            Q(experience__name__icontains=query)
            | Q(guide_name__icontains=query)
            | Q(block_reason__icontains=query)
        )
    if experience_id:
        slots_qs = slots_qs.filter(experience_id=experience_id)

    return {
        "experiences": [
            {
                "id": str(experience.id),
                "name": experience.name,
                "slug": experience.slug,
                "experience_type": experience.experience_type,
                "description": experience.description,
                "duration_minutes": experience.duration_minutes,
                "price_per_person": str(experience.price_per_person),
                "min_guests": experience.min_guests,
                "max_guests": experience.max_guests,
                "bookings_count": getattr(experience, "bookings_count", 0),
                "slots_count": getattr(experience, "slots_count", 0),
                "is_active": experience.is_active,
                "is_featured": experience.is_featured,
            }
            for experience in experiences_qs[:limit]
        ],
        "slots": [
            {
                "id": str(slot.id),
                "experience_id": str(slot.experience_id),
                "experience_name": slot.experience.name,
                "date": slot.date.isoformat(),
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "capacity": slot.capacity,
                "spots_available": slot.spots_available,
                "guide_name": slot.guide_name,
                "is_blocked": slot.is_blocked,
                "block_reason": slot.block_reason,
            }
            for slot in slots_qs[:limit]
        ],
        "bookings": [
            {
                "id": str(booking.id),
                "confirmation_code": booking.confirmation_code,
                "customer_name": booking.customer_name,
                "customer_email": booking.user.email if booking.user_id else booking.customer_email,
                "experience_name": booking.time_slot.experience.name,
                "experience_type": booking.time_slot.experience.experience_type,
                "slot_date": booking.time_slot.date.isoformat(),
                "slot_start_time": booking.time_slot.start_time.isoformat(),
                "slot_end_time": booking.time_slot.end_time.isoformat(),
                "guest_count": booking.guest_count,
                "status": booking.status,
                "special_requests": booking.special_requests,
                "checked_in_at": (
                    booking.checked_in_at.isoformat()
                    if booking.checked_in_at
                    else None
                ),
                "created_at": booking.created_at.isoformat(),
            }
            for booking in bookings_qs[:limit]
        ],
        "query": query,
        "status": status or None,
    }


def _payload_limit(payload: dict[str, object], *, default: int) -> int:
    raw_limit = payload.get("limit")
    if raw_limit in (None, ""):
        return default
    try:
        return max(1, min(int(str(raw_limit)), 20))
    except ValueError:
        return default
