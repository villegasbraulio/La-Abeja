"""Allowed order status transitions."""

from __future__ import annotations

from collections.abc import Mapping

from .models import Order

ALLOWED_ORDER_TRANSITIONS: Mapping[str, set[str]] = {
    Order.Status.PENDING_PAYMENT: {
        Order.Status.PAID,
        Order.Status.PAYMENT_FAILED,
        Order.Status.CANCELLED,
    },
    Order.Status.PAID: {Order.Status.PREPARING, Order.Status.REFUNDED},
    Order.Status.PREPARING: {Order.Status.READY_TO_SHIP, Order.Status.CANCELLED},
    Order.Status.READY_TO_SHIP: {Order.Status.SHIPPED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED, Order.Status.REFUNDED},
    Order.Status.DELIVERED: {Order.Status.REFUNDED},
    Order.Status.PAYMENT_FAILED: {Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED},
    Order.Status.CANCELLED: set(),
    Order.Status.REFUNDED: set(),
}


def can_transition(current_status: str, next_status: str) -> bool:
    """Return whether an order status transition is allowed."""
    return next_status in ALLOWED_ORDER_TRANSITIONS.get(current_status, set())
