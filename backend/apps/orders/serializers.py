"""Serializers for order checkout, shipping quotes, and retrieval."""

from __future__ import annotations

from decimal import Decimal
from typing import cast
from uuid import UUID

from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import Wine
from apps.notifications.email import EmailService
from apps.payments.models import Payment

from .access import build_guest_access_token
from .models import Order, OrderItem
from .shipping import (
    CheckoutShippingService,
    ShippingQuote,
    ShippingQuoteError,
    build_tracking_url,
)


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


class ShippingQuoteAddressSerializer(serializers.Serializer):
    """Validate destination data needed to quote a checkout shipment."""

    city = serializers.CharField(max_length=100)
    province = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100, required=False, default="Argentina")


class ShippingQuoteSerializer(serializers.Serializer):
    """Serialize a shipping quote returned by the checkout backend."""

    shipping_method = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    shipping_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    provider = serializers.CharField()
    service_level = serializers.CharField()
    estimated_delivery = serializers.DateField(allow_null=True)


class ShippingQuoteRequestSerializer(serializers.Serializer):
    """Quote available shipping methods for the current checkout cart."""

    items = CheckoutItemSerializer(many=True, allow_empty=False)
    shipping_address = ShippingQuoteAddressSerializer()

    def validate_items(
        self, items: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Reject duplicated wines when the quote is calculated."""
        wine_ids = [str(item["wine_id"]) for item in items]
        if len(wine_ids) != len(set(wine_ids)):
            raise serializers.ValidationError(
                "No se puede repetir el mismo vino en la cotización del checkout."
            )
        return items

    def get_quotes(self) -> list[dict[str, object]]:
        """Return serialized quotes for the current cart and destination."""
        checkout_items = cast(list[dict[str, object]], self.validated_data["items"])
        shipping_address = cast(dict[str, object], self.validated_data["shipping_address"])
        quantities_by_wine_id, wines = _load_checkout_wines(checkout_items)
        quotes = CheckoutShippingService().quote(
            wines=wines,
            quantities_by_wine_id=quantities_by_wine_id,
            shipping_address=shipping_address,
        )
        return ShippingQuoteSerializer(quotes, many=True).data


class OrderCreateSerializer(serializers.Serializer):
    """Create an order from checkout payload data."""

    items = CheckoutItemSerializer(many=True, allow_empty=False)
    shipping_method = serializers.ChoiceField(choices=Order.ShippingMethod.choices)
    shipping_address = CheckoutShippingAddressSerializer()
    customer_email = serializers.EmailField(required=False)
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
        user = request.user if request.user.is_authenticated else None
        checkout_items = cast(list[dict[str, object]], validated_data["items"])
        shipping_method = str(validated_data["shipping_method"])
        shipping_address = dict(cast(dict[str, object], validated_data["shipping_address"]))
        notes = cast(str, validated_data.get("notes", ""))
        customer_email = self._resolve_customer_email(validated_data)
        quantities_by_wine_id, wines = _load_checkout_wines(checkout_items)
        wine_map = {wine.id: wine for wine in wines}

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

        try:
            shipping_quote = CheckoutShippingService().quote_for_method(
                wines=wines,
                quantities_by_wine_id=quantities_by_wine_id,
                shipping_address=shipping_address,
                shipping_method=shipping_method,
            )
        except ShippingQuoteError as exc:
            raise serializers.ValidationError({"shipping_method": str(exc)}) from exc

        shipping_cost = shipping_quote.shipping_cost
        total = subtotal + shipping_cost
        shipping_address["_shipping_quote"] = _build_shipping_snapshot(shipping_quote)

        order = Order.objects.create(
            user=user,
            customer_email=customer_email,
            subtotal=subtotal,
            discount_amount=Decimal("0.00"),
            shipping_cost=shipping_cost,
            total=total,
            shipping_method=shipping_method,
            shipping_address=shipping_address,
            promo_code_used="",
            notes=str(notes),
            estimated_delivery=shipping_quote.estimated_delivery,
        )
        for order_item in order_items:
            order_item.order = order
        OrderItem.objects.bulk_create(order_items)

        hydrated_order = (
            Order.objects.select_related("user")
            .prefetch_related("items__wine__images")
            .get(pk=order.pk)
        )
        _send_order_confirmation_email(hydrated_order)
        return hydrated_order

    def _resolve_customer_email(self, validated_data: dict[str, object]) -> str:
        """Return the notification email for the current checkout."""
        request = self.context["request"]
        if request.user.is_authenticated:
            return str(request.user.email).strip().lower()

        customer_email = str(validated_data.get("customer_email") or "").strip().lower()
        if not customer_email:
            raise serializers.ValidationError(
                {"customer_email": "Necesitamos un email para enviarte el detalle del pedido."}
            )
        return customer_email


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


class OrderShippingQuoteSerializer(serializers.Serializer):
    """Expose the checkout shipping snapshot saved with the order."""

    provider = serializers.CharField()
    service_level = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    shipping_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    estimated_delivery = serializers.DateField(allow_null=True)


class OrderSerializer(serializers.ModelSerializer):
    """Serialize orders for list and detail screens."""

    items = OrderItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    shipping_quote = serializers.SerializerMethodField()
    guest_access_token = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()
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
            "customer_email",
            "shipping_address",
            "shipping_quote",
            "tracking_number",
            "tracking_url",
            "estimated_delivery",
            "notes",
            "items",
            "payment",
            "guest_access_token",
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

    def get_shipping_quote(self, obj: Order) -> dict[str, object] | None:
        """Return the shipping quote snapshot persisted at checkout time."""
        shipping_quote = obj.shipping_address.get("_shipping_quote")
        if not isinstance(shipping_quote, dict):
            return None
        serializer = OrderShippingQuoteSerializer(data=shipping_quote)
        if serializer.is_valid(raise_exception=False):
            return serializer.data
        return shipping_quote

    def get_guest_access_token(self, obj: Order) -> str | None:
        """Return a signed guest token when the order has no authenticated owner."""
        return build_guest_access_token(obj)

    def get_tracking_url(self, obj: Order) -> str | None:
        """Expose the public tracking URL when one exists."""
        return build_tracking_url(obj.tracking_number)


def _load_checkout_wines(
    checkout_items: list[dict[str, object]],
) -> tuple[dict[UUID, int], list[Wine]]:
    """Load the active wines required by a checkout payload."""
    wine_ids = [cast(UUID, item["wine_id"]) for item in checkout_items]
    wines = list(
        Wine.objects.select_related("category", "varietal")
        .filter(id__in=wine_ids, is_active=True)
    )
    wine_map = {wine.id: wine for wine in wines}
    if len(wine_map) != len(wine_ids):
        raise serializers.ValidationError(
            {"items": "Uno o más vinos no existen o no están disponibles."}
        )
    quantities_by_wine_id = {
        cast(UUID, item["wine_id"]): cast(int, item["quantity"]) for item in checkout_items
    }
    return quantities_by_wine_id, wines


def _build_shipping_snapshot(shipping_quote: ShippingQuote) -> dict[str, object]:
    """Return a JSON-safe quote snapshot to embed in the order address."""
    return {
        "provider": shipping_quote.provider,
        "service_level": shipping_quote.service_level,
        "label": shipping_quote.label,
        "description": shipping_quote.description,
        "shipping_cost": str(shipping_quote.shipping_cost),
        "estimated_delivery": (
            shipping_quote.estimated_delivery.isoformat()
            if shipping_quote.estimated_delivery
            else None
        ),
    }


def _send_order_confirmation_email(order: Order) -> None:
    """Send the confirmation email once the order items already exist."""
    if not order.customer_email:
        return

    items_summary = " | ".join(
        f"{item.quantity}x {item.wine_name} ({item.subtotal})"
        for item in order.items.all()
    )
    EmailService.send_transactional(
        to=order.customer_email,
        template="order_confirmation",
        context={
            "order_number": order.order_number,
            "status": order.get_status_display(),
            "total": order.total,
            "shipping_method": order.get_shipping_method_display(),
            "estimated_delivery": order.estimated_delivery or "A coordinar",
            "tracking_number": order.tracking_number or "Pendiente de asignación",
            "tracking_url": build_tracking_url(order.tracking_number) or "Pendiente",
            "items": items_summary,
        },
    )
