"""Guest-access helpers for anonymous visit bookings."""

from __future__ import annotations

from django.core import signing

from .models import Booking

GUEST_ACCESS_SALT = "reservations.guest-access"
GUEST_ACCESS_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def build_guest_access_token(booking: Booking) -> str | None:
    """Return a signed guest token for bookings without an authenticated owner."""
    if booking.user_id or not booking.customer_email:
        return None
    return signing.dumps(
        {
            "booking_id": str(booking.id),
            "customer_email": booking.customer_email,
        },
        salt=GUEST_ACCESS_SALT,
    )


def resolve_guest_booking(booking_id: str, guest_access_token: str | None) -> Booking | None:
    """Return the guest booking when the token is valid for the requested id."""
    if not guest_access_token:
        return None

    try:
        payload = signing.loads(
            guest_access_token,
            salt=GUEST_ACCESS_SALT,
            max_age=GUEST_ACCESS_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        return None
    except signing.SignatureExpired:
        return None

    signed_booking_id = str(payload.get("booking_id") or "")
    signed_customer_email = str(payload.get("customer_email") or "").strip().lower()
    if signed_booking_id != str(booking_id) or not signed_customer_email:
        return None

    return (
        Booking.objects.select_related("user", "time_slot", "time_slot__experience")
        .filter(
            pk=booking_id,
            user__isnull=True,
            customer_email__iexact=signed_customer_email,
        )
        .first()
    )
