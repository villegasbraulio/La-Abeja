"""Order and cart models."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class PromoCode(models.Model):
    """Promo code for carts and orders."""

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Porcentaje"
        FIXED = "fixed", "Monto fijo"
        FREE_SHIPPING = "free_shipping", "Envío gratis"

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        """Return the promo code identifier."""
        return self.code

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """Calculate the promo discount for a subtotal."""
        if subtotal < self.min_order_amount:
            return Decimal("0.00")
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return (subtotal * self.discount_value) / Decimal("100")
        if self.discount_type == self.DiscountType.FIXED:
            return min(subtotal, self.discount_value)
        return Decimal("0.00")


class Cart(models.Model):
    """Shopping cart for authenticated or anonymous users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(default=timezone.now)
    abandon_reminder_sent = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return a cart label for admins and logs."""
        return str(self.id)

    @property
    def subtotal(self) -> Decimal:
        """Return the cart subtotal."""
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))

    @property
    def discount_amount(self) -> Decimal:
        """Return the active discount amount."""
        if self.promo_code:
            return self.promo_code.calculate_discount(self.subtotal)
        return Decimal("0.00")

    @property
    def total(self) -> Decimal:
        """Return the total after discounts."""
        return self.subtotal - self.discount_amount


class CartItem(models.Model):
    """Line item in a cart."""

    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    wine = models.ForeignKey("catalog.Wine", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return a concise line item label."""
        return f"{self.wine.name} x{self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        """Return the line subtotal."""
        return self.unit_price * self.quantity


class ShippingAddress(models.Model):
    """Saved shipping address."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="addresses",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=50)
    recipient_name = models.CharField(max_length=200)
    street = models.CharField(max_length=300)
    number = models.CharField(max_length=20)
    floor_apt = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Argentina")
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return a useful address label."""
        return f"{self.label} - {self.city}"


class Order(models.Model):
    """Completed checkout order."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Esperando pago"
        PAYMENT_FAILED = "payment_failed", "Pago fallido"
        PAID = "paid", "Pagado"
        PREPARING = "preparing", "Preparando"
        READY_TO_SHIP = "ready_to_ship", "Listo para enviar"
        SHIPPED = "shipped", "En camino"
        DELIVERED = "delivered", "Entregado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    class ShippingMethod(models.TextChoices):
        STANDARD = "standard", "Envío estándar (5-7 días)"
        EXPRESS = "express", "Envío express (2-3 días)"
        PICKUP = "pickup", "Retiro en bodega"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    customer_email = models.EmailField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_method = models.CharField(max_length=20, choices=ShippingMethod.choices)
    shipping_address = models.JSONField(default=dict)
    promo_code_used = models.CharField(max_length=50, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    status_email_sent = models.JSONField(default=dict, blank=True)
    review_request_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return the order number."""
        return self.order_number or str(self.id)

    def save(self, *args: object, **kwargs: object) -> None:
        """Assign an order number on first save."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self) -> str:
        """Generate the next human-friendly order number."""
        year = timezone.now().year
        count = Order.objects.filter(created_at__year=year).count() + 1
        return f"LAB-{year}-{count:06d}"


class OrderItem(models.Model):
    """Snapshot of a purchased wine line item."""

    order = models.ForeignKey(Order, related_name="items", on_delete=models.PROTECT)
    wine = models.ForeignKey("catalog.Wine", on_delete=models.PROTECT)
    wine_name = models.CharField(max_length=200)
    wine_sku = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        """Return the purchased line item label."""
        return f"{self.wine_name} x{self.quantity}"


class AndreaniShipment(models.Model):
    """Persistent, idempotent record of an Andreani shipment request."""

    class Status(models.TextChoices):
        PROCESSING = "processing", "Procesando"
        CREATED = "created", "Creado"
        FAILED = "failed", "Fallido"

    order = models.OneToOneField(
        Order,
        related_name="andreani_shipment",
        on_delete=models.PROTECT,
    )
    idempotency_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
    )
    tracking_number = models.CharField(max_length=100, blank=True)
    request_payload = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    response_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    label_source_url = models.URLField(max_length=1000, blank=True)
    label = models.FileField(upload_to="andreani/labels/%Y/%m/%d", blank=True)
    label_error = models.TextField(blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return the local order and current Andreani state."""
        return f"{self.order.order_number} - {self.get_status_display()}"
