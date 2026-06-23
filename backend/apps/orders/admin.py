"""Admin configuration for orders, carts and promotions."""

from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet

from .models import (
    AndreaniShipment,
    Cart,
    CartItem,
    Order,
    OrderItem,
    PromoCode,
    ShippingAddress,
)


class CartItemInline(admin.TabularInline):
    """Inline view for cart items."""

    model = CartItem
    extra = 0
    autocomplete_fields = ("wine",)
    readonly_fields = ("subtotal_display", "added_at")
    fields = ("wine", "quantity", "unit_price", "subtotal_display", "added_at")

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: CartItem) -> object:
        """Return the line subtotal."""
        return obj.subtotal


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Read-friendly cart admin for customer support."""

    list_display = (
        "id",
        "user",
        "item_count",
        "subtotal_display",
        "abandon_reminder_sent",
        "updated_at",
    )
    list_filter = ("abandon_reminder_sent", "created_at", "updated_at")
    search_fields = ("id", "user__email", "session_key")
    autocomplete_fields = ("user", "promo_code")
    inlines = [CartItemInline]
    readonly_fields = (
        "subtotal_display",
        "discount_display",
        "total_display",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Cliente", {"fields": (("user", "session_key"), "promo_code")}),
        (
            "Totales",
            {"fields": ("subtotal_display", "discount_display", "total_display")},
        ),
        (
            "Seguimiento",
            {
                "fields": (
                    "abandon_reminder_sent",
                    "last_activity_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="Items")
    def item_count(self, obj: Cart) -> int:
        """Return the number of lines in the cart."""
        return obj.items.count()

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: Cart) -> object:
        """Return the cart subtotal."""
        return obj.subtotal

    @admin.display(description="Descuento")
    def discount_display(self, obj: Cart) -> object:
        """Return the cart discount amount."""
        return obj.discount_amount

    @admin.display(description="Total")
    def total_display(self, obj: Cart) -> object:
        """Return the cart total."""
        return obj.total


class OrderItemInline(admin.TabularInline):
    """Read-only order item snapshot inline."""

    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("wine_name", "wine_sku", "quantity", "unit_price", "subtotal")
    readonly_fields = ("wine_name", "wine_sku", "quantity", "unit_price", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Operations-focused order admin."""

    list_display = ("order_number", "user", "status", "total", "shipping_method", "created_at")
    list_filter = ("status", "shipping_method", "created_at")
    search_fields = ("order_number", "user__email", "tracking_number", "promo_code_used")
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
    readonly_fields = (
        "order_number",
        "subtotal",
        "discount_amount",
        "shipping_cost",
        "total",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Resumen",
            {
                "fields": (
                    ("order_number", "status"),
                    "user",
                    ("shipping_method", "promo_code_used"),
                )
            },
        ),
        (
            "Totales",
            {"fields": (("subtotal", "discount_amount"), ("shipping_cost", "total"))},
        ),
        (
            "Entrega",
            {
                "fields": (
                    "shipping_address",
                    ("tracking_number", "estimated_delivery"),
                    ("shipped_at", "delivered_at"),
                )
            },
        ),
        (
            "Automatizaciones y notas",
            {"fields": ("status_email_sent", "review_request_sent", "notes")},
        ),
        ("Fechas", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [OrderItemInline]
    actions = ("mark_as_preparing", "mark_as_ready_to_ship", "mark_as_shipped", "mark_as_delivered")

    @admin.action(description="Marcar como preparando")
    def mark_as_preparing(self, request: object, queryset: QuerySet[Order]) -> None:
        """Bulk move selected orders to preparing."""
        queryset.update(status=Order.Status.PREPARING)

    @admin.action(description="Marcar como listo para enviar")
    def mark_as_ready_to_ship(self, request: object, queryset: QuerySet[Order]) -> None:
        """Bulk move selected orders to ready-to-ship."""
        queryset.update(status=Order.Status.READY_TO_SHIP)

    @admin.action(description="Marcar como enviado")
    def mark_as_shipped(self, request: object, queryset: QuerySet[Order]) -> None:
        """Bulk move selected orders to shipped."""
        queryset.update(status=Order.Status.SHIPPED)

    @admin.action(description="Marcar como entregado")
    def mark_as_delivered(self, request: object, queryset: QuerySet[Order]) -> None:
        """Bulk move selected orders to delivered."""
        queryset.update(status=Order.Status.DELIVERED)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """Promo code admin optimized for marketing operations."""

    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "min_order_amount",
        "usage_display",
        "valid_until",
        "is_active",
    )
    list_editable = ("is_active",)
    list_filter = ("discount_type", "is_active", "valid_until")
    search_fields = ("code",)
    readonly_fields = ("used_count",)
    fieldsets = (
        ("Código", {"fields": ("code", "discount_type", "discount_value")}),
        ("Reglas", {"fields": (("min_order_amount", "max_uses"), "used_count")}),
        ("Vigencia", {"fields": (("valid_from", "valid_until"), "is_active")}),
    )

    @admin.display(description="Uso")
    def usage_display(self, obj: PromoCode) -> str:
        """Return a human-friendly usage summary."""
        if obj.max_uses:
            return f"{obj.used_count}/{obj.max_uses}"
        return f"{obj.used_count}/∞"


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    """Address admin for customer support."""

    list_display = ("label", "recipient_name", "user", "city", "province", "is_default")
    list_filter = ("province", "is_default")
    search_fields = ("recipient_name", "user__email", "city", "postal_code")
    autocomplete_fields = ("user",)


@admin.register(AndreaniShipment)
class AndreaniShipmentAdmin(admin.ModelAdmin):
    """Read-only operational audit trail for Andreani requests."""

    list_display = (
        "order",
        "status",
        "tracking_number",
        "response_status_code",
        "attempt_count",
        "created_at",
    )
    list_filter = ("status", "response_status_code", "created_at")
    search_fields = ("order__order_number", "tracking_number", "idempotency_key")
    readonly_fields = (
        "order",
        "idempotency_key",
        "status",
        "tracking_number",
        "request_payload",
        "raw_response",
        "response_status_code",
        "attempt_count",
        "label_source_url",
        "label",
        "label_error",
        "last_error",
        "created_at",
        "updated_at",
    )
