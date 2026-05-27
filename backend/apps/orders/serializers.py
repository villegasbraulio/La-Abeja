"""Serializers for order checkout and retrieval."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Wine
from apps.payments.models import Payment

from .models import Order, OrderItem

SHIPPING_COSTS: dict[str, Decimal] = {
    Order.ShippingMethod.STANDARD: Decimal("3500.00"),
    Order.ShippingMethod.EXPRESS: Decimal("6500.00"),
    Order.ShippingMethod.PICKUP: Decimal("0.00"),
}


def estimate_delivery_date(shipping_method: str) -> date | None:
    """Return an estimated delivery date for the selected shipping method."""
    today = timezone.localdate()
    if shipping_method == Order.ShippingMethod.STANDARD:
        return today + timedelta(days=7)
    if shipping_method == Order.ShippingMethod.EXPRESS:
        return today + timedelta(days=3)
    return None


class CheckoutItemSerializer(serializers.Serializer):
    """Validate a local cart line sent from the frontend checkout."""

    wine_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=24)


class CheckoutShippingAddressSerializer(serializers.Serializer):
    """Validate the shipping snapshot received during checkout."""

    recipient_name = serializers.CharField(max_length=200)
    street = serializers.CharField(max_length=300)
    number = serializers.CharField(max_length=20)
    floor_apt = serializers.CharField(max_length=50, allow_blank=True, required=False)
    city = serializers.CharField(max_length=100)
    province = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100, required=False, default="Argentina")
    phone = serializers.CharField(max_length=20)


class OrderCreateSerializer(serializers.Serializer):
    """Create an order from checkout payload data."""

    items = CheckoutItemSerializer(many=True, allow_empty=False)
    shipping_method = serializers.ChoiceField(choices=Order.ShippingMethod.choices)
    shipping_address = CheckoutShippingAddressSerializer()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_items(
        self, items: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Reject duplicated wines in a single checkout payload."""
        wine_ids = [str(item["wine_id"]) for item in items]
        if len(wine_ids) != len(set(wine_ids)):
            raise serializers.ValidationError(
                "No se puede repetir el mismo vino en el payload del checkout."
            )
        return items

    @transaction.atomic
    def create(self, validated_data: dict[str, object]) -> Order:
        """Persist the order and its immutable line item snapshots."""
        request = self.context["request"]
        user = request.user
        checkout_items = cast(list[dict[str, object]], validated_data["items"])
        shipping_method = str(validated_data["shipping_method"])
        shipping_address = cast(dict[str, object], validated_data["shipping_address"])
        notes = cast(str, validated_data.get("notes", ""))

        wine_ids = [item["wine_id"] for item in checkout_items]
        wines = (
            Wine.objects.select_related("category", "varietal")
            .filter(id__in=wine_ids, is_active=True)
        )
        wine_map = {wine.id: wine for wine in wines}

        if len(wine_map) != len(wine_ids):
            raise serializers.ValidationError(
                {"items": "Uno o más vinos no existen o no están disponibles."}
            )

        subtotal = Decimal("0.00")
        order_items: list[OrderItem] = []
        for item in checkout_items:
            wine_id = cast(UUID, item["wine_id"])
            quantity = cast(int, item["quantity"])
            wine = wine_map[wine_id]
            if wine.stock < quantity:
                raise serializers.ValidationError(
                    {
                        "items": (
                            f"No hay stock suficiente para {wine.name}. "
                            f"Disponible: {wine.stock}."
                        )
                    }
                )
            line_subtotal = wine.price * quantity
            subtotal += line_subtotal
            order_items.append(
                OrderItem(
                    wine=wine,
                    wine_name=wine.name,
                    wine_sku=wine.sku,
                    quantity=quantity,
                    unit_price=wine.price,
                    subtotal=line_subtotal,
                )
            )

        shipping_cost = SHIPPING_COSTS[str(shipping_method)]
        total = subtotal + shipping_cost

        order = Order.objects.create(
            user=user,
            subtotal=subtotal,
            discount_amount=Decimal("0.00"),
            shipping_cost=shipping_cost,
            total=total,
            shipping_method=shipping_method,
            shipping_address=shipping_address,
            promo_code_used="",
            notes=str(notes),
            estimated_delivery=estimate_delivery_date(str(shipping_method)),
        )
        for order_item in order_items:
            order_item.order = order
        OrderItem.objects.bulk_create(order_items)

        return (
            Order.objects.select_related("user")
            .prefetch_related("items__wine__images")
            .get(pk=order.pk)
        )


class OrderItemSerializer(serializers.ModelSerializer):
    """Serialize immutable purchased line items."""

    wine_slug = serializers.CharField(source="wine.slug", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "wine_name",
            "wine_sku",
            "wine_slug",
            "quantity",
            "unit_price",
            "subtotal",
            "primary_image",
        ]

    def get_primary_image(self, obj: OrderItem) -> str | None:
        """Expose the wine primary image when it still exists."""
        image = obj.wine.images.filter(is_primary=True).first()
        return image.url if image else None


class PaymentSummarySerializer(serializers.Serializer):
    """Serialize the payment snapshot attached to an order."""

    id = serializers.UUIDField()
    status = serializers.CharField()
    status_detail = serializers.CharField()
    mp_preference_id = serializers.CharField()
    mp_payment_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField()
    payment_type = serializers.CharField()
    installments = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class OrderSerializer(serializers.ModelSerializer):
    """Serialize orders for list and detail screens."""

    items = OrderItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    shipping_method_label = serializers.CharField(
        source="get_shipping_method_display",
        read_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_label",
            "subtotal",
            "discount_amount",
            "shipping_cost",
            "total",
            "shipping_method",
            "shipping_method_label",
            "shipping_address",
            "tracking_number",
            "estimated_delivery",
            "notes",
            "items",
            "payment",
            "created_at",
            "updated_at",
        ]

    def get_payment(self, obj: Order) -> dict[str, object] | None:
        """Return payment details when the order already has a payment record."""
        try:
            payment = obj.payment
        except Payment.DoesNotExist:
            return None
        return PaymentSummarySerializer(payment).data
