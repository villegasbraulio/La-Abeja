"""Guest-access helpers for anonymous checkout orders."""

from __future__ import annotations

from django.core import signing

from .models import Order

GUEST_ACCESS_SALT = "orders.guest-access"
GUEST_ACCESS_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def build_guest_access_token(order: Order) -> str | None:
    """Return a signed guest token for orders without an authenticated owner."""
    if order.user_id or not order.customer_email:
        return None
    return signing.dumps(
        {
            "order_id": str(order.id),
            "customer_email": order.customer_email,
        },
        salt=GUEST_ACCESS_SALT,
    )


def resolve_guest_order(order_id: str, guest_access_token: str | None) -> Order | None:
    """Return the guest order when the token is valid for the requested id."""
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

    signed_order_id = str(payload.get("order_id") or "")
    signed_customer_email = str(payload.get("customer_email") or "").strip().lower()
    if signed_order_id != str(order_id) or not signed_customer_email:
        return None

    return (
        Order.objects.select_related("user")
        .prefetch_related("items__wine__images")
        .filter(
            pk=order_id,
            user__isnull=True,
            customer_email__iexact=signed_customer_email,
        )
        .first()
    )
