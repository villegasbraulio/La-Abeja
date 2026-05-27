"""Serializers for payment flows."""

from __future__ import annotations

from rest_framework import serializers

from apps.orders.models import Order

from .mercadopago import MercadoPagoClient
from .models import Payment


class CreatePreferenceSerializer(serializers.Serializer):
    """Validate and create a Checkout Pro payment preference."""

    order_id = serializers.UUIDField()

    def validate_order_id(self, value):
        """Ensure the order belongs to the current user and can be paid."""
        request = self.context["request"]
        order = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .select_related("user")
            .filter(pk=value)
            .first()
        )
        if order is None:
            raise serializers.ValidationError("No encontramos ese pedido.")
        if order.status not in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED}:
            raise serializers.ValidationError("Este pedido ya no admite un nuevo intento de pago.")
        if not order.items.exists():
            raise serializers.ValidationError("El pedido no tiene productos para cobrar.")
        self.context["order"] = order
        return value

    def create_preference(self) -> dict[str, object]:
        """Create a Mercado Pago preference and persist the payment record."""
        order: Order = self.context["order"]
        preference = MercadoPagoClient().create_preference(order)
        Payment.objects.update_or_create(
            order=order,
            defaults={
                "mp_preference_id": str(preference["id"]),
                "status": Payment.Status.PENDING,
                "amount": order.total,
                "currency": "ARS",
            },
        )
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "preference_id": str(preference["id"]),
            "init_point": preference.get("init_point"),
            "sandbox_init_point": preference.get("sandbox_init_point"),
        }
