"""Serializers for payment flows."""

from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from apps.orders.access import resolve_guest_order
from apps.orders.models import Order

from .mercadopago import MercadoPagoClient
from .models import Payment


class PaymentOrderResolutionMixin:
    """Share order resolution rules between payment endpoints."""

    def _resolve_order(self, *, request, order_id):
        """Return the current user's order or a guest order with a valid token."""
        if request.user.is_authenticated:
            return (
                Order.objects.filter(user=request.user)
                .prefetch_related("items")
                .select_related("user")
                .filter(pk=order_id)
                .first()
            )

        guest_access_token = self.initial_data.get("guest_access_token")
        guest_order = resolve_guest_order(
            order_id=str(order_id),
            guest_access_token=str(guest_access_token or ""),
        )
        if guest_order is None:
            return None
        return guest_order


class CreatePreferenceSerializer(PaymentOrderResolutionMixin, serializers.Serializer):
    """Validate and create a Checkout Pro payment preference."""

    order_id = serializers.UUIDField()
    guest_access_token = serializers.CharField(required=False, allow_blank=False)

    def validate_order_id(self, value):
        """Ensure the order belongs to the current user and can be paid."""
        request = self.context["request"]
        order = self._resolve_order(request=request, order_id=value)
        if order is None:
            raise serializers.ValidationError("No encontramos ese pedido.")
        if order.status not in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED}:
            raise serializers.ValidationError("Este pedido ya no admite un nuevo intento de pago.")
        if not order.items.exists():
            raise serializers.ValidationError("El pedido no tiene productos para cobrar.")
        self.context["order"] = order
        return value

    @transaction.atomic
    def create_preference(self) -> dict[str, object]:
        """Return one stable Mercado Pago preference for the local order."""
        validated_order: Order = self.context["order"]
        order = (
            Order.objects.select_for_update()
            .select_related("user")
            .prefetch_related("items")
            .get(pk=validated_order.pk)
        )
        if order.status not in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED}:
            raise serializers.ValidationError(
                {"order_id": "Este pedido ya no admite un nuevo intento de pago."}
            )

        idempotency_key = f"mercadopago:preference:{order.id}"
        payment, _ = Payment.objects.select_for_update().get_or_create(
            order=order,
            defaults={
                "idempotency_key": idempotency_key,
                "mp_preference_id": "",
                "status": Payment.Status.PENDING,
                "amount": order.total,
                "currency": "ARS",
            },
        )
        if payment.mp_preference_id:
            return self._preference_response(order, payment)

        preference = MercadoPagoClient().create_preference(
            order,
            idempotency_key=payment.idempotency_key,
        )
        payment.mp_preference_id = str(preference["id"])
        payment.preference_init_point = str(preference.get("init_point") or "")
        payment.preference_sandbox_init_point = str(
            preference.get("sandbox_init_point") or ""
        )
        payment.status = Payment.Status.PENDING
        payment.amount = order.total
        payment.currency = "ARS"
        payment.save(
            update_fields=[
                "mp_preference_id",
                "preference_init_point",
                "preference_sandbox_init_point",
                "status",
                "amount",
                "currency",
                "updated_at",
            ]
        )
        return self._preference_response(order, payment)

    def _preference_response(self, order: Order, payment: Payment) -> dict[str, object]:
        """Serialize a newly created or safely reused payment preference."""
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "preference_id": payment.mp_preference_id,
            "init_point": payment.preference_init_point or None,
            "sandbox_init_point": payment.preference_sandbox_init_point or None,
        }
