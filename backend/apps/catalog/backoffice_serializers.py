"""Serializers for the custom backoffice API."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.template.defaultfilters import slugify
from rest_framework import serializers

from apps.authentication.models import CustomUser
from apps.orders.models import Order, PromoCode
from apps.orders.serializers import OrderSerializer
from apps.orders.state_machine import can_transition
from apps.payments.models import Payment

from .models import Category, Varietal, Wine, WineImage


class BackofficeCategorySerializer(serializers.ModelSerializer):
    """Category serializer with business-friendly extras."""

    wines_count = serializers.IntegerField(read_only=True)
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "icon", "order", "wines_count"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Auto-generate a slug when the operator leaves it blank."""
        name = str(attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = str(attrs.get("slug") or "").strip()
        if name and not slug:
            attrs["slug"] = slugify(name)
        return attrs


class BackofficeVarietalSerializer(serializers.ModelSerializer):
    """Varietal serializer for the internal catalog team."""

    wines_count = serializers.IntegerField(read_only=True)
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Varietal
        fields = ["id", "name", "slug", "description", "origin_region", "wines_count"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Auto-generate a slug when the operator leaves it blank."""
        name = str(attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = str(attrs.get("slug") or "").strip()
        if name and not slug:
            attrs["slug"] = slugify(name)
        return attrs


class BackofficeWineImageSerializer(serializers.ModelSerializer):
    """Serialize editable wine images."""

    id = serializers.IntegerField(required=False)

    class Meta:
        model = WineImage
        fields = ["id", "url", "alt_text", "is_primary", "order"]


class BackofficeWineListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the wine manager changelist."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    varietal_name = serializers.CharField(source="varietal.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    stock_state = serializers.SerializerMethodField()
    gross_margin_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Wine
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "category_name",
            "varietal",
            "varietal_name",
            "price",
            "compare_at_price",
            "stock",
            "low_stock_threshold",
            "is_active",
            "is_featured",
            "is_limited_edition",
            "primary_image",
            "stock_state",
            "gross_margin_percentage",
            "updated_at",
        ]

    def get_primary_image(self, obj: Wine) -> str | None:
        """Return the current primary image URL."""
        image = obj.images.filter(is_primary=True).first() or obj.images.first()
        return image.url if image else None

    def get_stock_state(self, obj: Wine) -> str:
        """Return a human-friendly stock state."""
        if obj.stock <= 0:
            return "out"
        if obj.stock <= obj.low_stock_threshold:
            return "low"
        return "healthy"

    def get_gross_margin_percentage(self, obj: Wine) -> int | None:
        """Estimate the gross margin percentage."""
        if obj.price <= 0:
            return None
        margin = ((obj.price - obj.cost_price) / obj.price) * Decimal("100")
        return int(margin)


class BackofficeWineDetailSerializer(BackofficeWineListSerializer):
    """Full serializer used by the custom backoffice forms."""

    images = BackofficeWineImageSerializer(many=True, required=False)
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta(BackofficeWineListSerializer.Meta):
        fields = BackofficeWineListSerializer.Meta.fields + [
            "blend_varietals",
            "vintage_year",
            "cost_price",
            "alcohol_percentage",
            "serving_temperature_min",
            "serving_temperature_max",
            "ageing_months",
            "ageing_type",
            "tannins",
            "acidity",
            "body",
            "sweetness",
            "fruit_intensity",
            "description",
            "tasting_notes",
            "pairing_suggestions",
            "winemaker_notes",
            "awards",
            "meta_title",
            "meta_description",
            "images",
            "created_at",
        ]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Auto-generate slugs and normalize image primaries."""
        name = str(attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = str(attrs.get("slug") or "").strip()
        if name and not slug:
            attrs["slug"] = slugify(name)

        images = attrs.get("images")
        if isinstance(images, list) and len(images) > 0:
            primary_count = sum(1 for image in images if image.get("is_primary"))
            if primary_count == 0:
                images[0]["is_primary"] = True
            elif primary_count > 1:
                raise serializers.ValidationError(
                    {"images": "Solo una imagen puede ser primaria."}
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, object]) -> Wine:
        """Create a wine and its images in one transaction."""
        images = validated_data.pop("images", [])
        wine = Wine.objects.create(**validated_data)
        self._replace_images(wine, images)
        return wine

    @transaction.atomic
    def update(self, instance: Wine, validated_data: dict[str, object]) -> Wine:
        """Update a wine and replace its images when provided."""
        images = validated_data.pop("images", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if images is not None:
            self._replace_images(instance, images)
        return instance

    def _replace_images(self, wine: Wine, images: object) -> None:
        """Replace the full image set with the payload from the backoffice."""
        if not isinstance(images, list):
            return
        wine.images.all().delete()
        for index, image in enumerate(images):
            if not isinstance(image, dict):
                continue
            WineImage.objects.create(
                wine=wine,
                url=str(image.get("url", "")),
                alt_text=str(image.get("alt_text", "")),
                is_primary=bool(image.get("is_primary", False)),
                order=int(image.get("order", index)),
            )


class BackofficeDashboardSerializer(serializers.Serializer):
    """Serialize dashboard summary data for the internal panel."""

    total_wines = serializers.IntegerField()
    active_wines = serializers.IntegerField()
    featured_wines = serializers.IntegerField()
    low_stock_wines = serializers.IntegerField()
    categories = serializers.IntegerField()
    varietals = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    low_stock_items = serializers.ListField(child=serializers.DictField())
    action_items = serializers.ListField(child=serializers.DictField())


class BackofficeOrderListSerializer(serializers.ModelSerializer):
    """Lightweight order serializer for the internal operations queue."""

    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_status_label = serializers.SerializerMethodField()
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
            "customer_name",
            "customer_email",
            "customer_phone",
            "status",
            "status_label",
            "payment_status",
            "payment_status_label",
            "shipping_method",
            "shipping_method_label",
            "total",
            "item_count",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj: Order) -> str:
        """Return a business-friendly customer display name."""
        if obj.user_id and obj.user:
            full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            if full_name:
                return full_name
            if obj.user.email:
                return obj.user.email

        recipient_name = str(obj.shipping_address.get("recipient_name", "")).strip()
        if recipient_name:
            return recipient_name
        return obj.customer_email or "Sin cliente"

    def get_customer_email(self, obj: Order) -> str:
        """Return the authenticated email or the guest checkout contact."""
        if obj.user_id and obj.user and obj.user.email:
            return obj.user.email
        return obj.customer_email

    def get_customer_phone(self, obj: Order) -> str:
        """Return the authenticated phone or the shipping contact phone."""
        if obj.user_id and obj.user and obj.user.phone:
            return obj.user.phone
        return str(obj.shipping_address.get("phone", "")).strip()

    def get_item_count(self, obj: Order) -> int:
        """Return the total number of bottles in the order."""
        return sum(item.quantity for item in obj.items.all())

    def get_payment_status(self, obj: Order) -> str | None:
        """Expose the linked payment status when it exists."""
        try:
            return obj.payment.status
        except Payment.DoesNotExist:
            return None

    def get_payment_status_label(self, obj: Order) -> str | None:
        """Return the payment status label for internal operators."""
        try:
            return Payment.Status(obj.payment.status).label
        except (Payment.DoesNotExist, ValueError):
            return None


class BackofficeOrderDetailSerializer(OrderSerializer):
    """Detailed order serializer for the custom backoffice panel."""

    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = [
            "customer_name",
            "customer_email",
            "customer_phone",
            *OrderSerializer.Meta.fields,
        ]

    def get_customer_name(self, obj: Order) -> str:
        """Return the customer's full name or fallback to email."""
        return BackofficeOrderListSerializer.get_customer_name(self, obj)

    def get_customer_email(self, obj: Order) -> str:
        """Return the best contact email for the order."""
        return BackofficeOrderListSerializer.get_customer_email(self, obj)

    def get_customer_phone(self, obj: Order) -> str:
        """Return the best contact phone for the order."""
        return BackofficeOrderListSerializer.get_customer_phone(self, obj)


class BackofficeOrderActionSerializer(serializers.Serializer):
    """Validate the small set of order operations exposed to staff."""

    status = serializers.ChoiceField(choices=Order.Status.choices, required=False)
    tracking_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    estimated_delivery = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, value: str) -> str:
        """Keep staff actions inside the order state machine."""
        order = self.context["order"]
        if value != order.status and not can_transition(order.status, value):
            raise serializers.ValidationError(
                f"No se puede pasar de {order.get_status_display()} a {Order.Status(value).label}."
            )
        return value

    def save(self) -> Order:
        """Apply the requested operational changes."""
        order = self.context["order"]
        update_fields = ["updated_at"]
        for field in ["status", "tracking_number", "estimated_delivery", "notes"]:
            if field in self.validated_data:
                setattr(order, field, self.validated_data[field])
                update_fields.append(field)
        order.save(update_fields=update_fields)
        return order


class BackofficePromoCodeSerializer(serializers.ModelSerializer):
    """Expose promo codes in the custom backoffice."""

    class Meta:
        model = PromoCode
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "max_uses",
            "used_count",
            "valid_from",
            "valid_until",
            "is_active",
        ]
        read_only_fields = ["used_count"]


class BackofficeCustomerSerializer(serializers.ModelSerializer):
    """Small customer 360 row for the backoffice."""

    full_name = serializers.CharField(read_only=True)
    orders_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "newsletter_subscribed",
            "orders_count",
            "total_spent",
            "last_order_at",
            "date_joined",
        ]
