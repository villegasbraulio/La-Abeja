"""Reservation models."""

from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models


class Experience(models.Model):
    """Bookable winery experience."""

    class ExperienceType(models.TextChoices):
        WINERY_TOUR = "winery_tour", "Tour por la Bodega"
        PREMIUM_TASTING = "premium_tasting", "Cata Premium"
        HARVEST = "harvest", "Experiencia de Vendimia"
        PRIVATE_EVENT = "private_event", "Evento Privado"
        WINE_PAIRING = "wine_pairing", "Maridaje con Chef"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    experience_type = models.CharField(max_length=30, choices=ExperienceType.choices)
    description = models.TextField()
    duration_minutes = models.IntegerField()
    price_per_person = models.DecimalField(max_digits=8, decimal_places=2)
    min_guests = models.IntegerField(default=1)
    max_guests = models.IntegerField()
    includes = models.JSONField(default=list, blank=True)
    highlights = models.JSONField(default=list, blank=True)
    cover_image = models.URLField()
    gallery_images = models.JSONField(default=list, blank=True)
    cancellation_hours = models.IntegerField(default=24)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return the experience name."""
        return self.name


class TimeSlot(models.Model):
    """Time slot for an experience."""

    experience = models.ForeignKey(Experience, related_name="slots", on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.IntegerField()
    spots_available = models.IntegerField()
    guide_name = models.CharField(max_length=100, blank=True)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("experience", "date", "start_time")
        indexes = [models.Index(fields=["date", "experience"])]

    def __str__(self) -> str:
        """Return the slot label."""
        return f"{self.experience.name} · {self.date} {self.start_time}"


class Booking(models.Model):
    """Customer booking."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Esperando pago"
        PAYMENT_FAILED = "payment_failed", "Pago fallido"
        CONFIRMED = "confirmed", "Confirmada"
        CANCELLED = "cancelled", "Cancelada"
        COMPLETED = "completed", "Completada"
        NO_SHOW = "no_show", "No se presentó"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    confirmation_code = models.CharField(max_length=10, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookings",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    time_slot = models.ForeignKey(TimeSlot, related_name="bookings", on_delete=models.PROTECT)
    customer_first_name = models.CharField(max_length=100, blank=True)
    customer_last_name = models.CharField(max_length=100, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    guest_count = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    special_requests = models.TextField(blank=True)
    dietary_restrictions = models.JSONField(default=list, blank=True)
    qr_code_url = models.URLField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    client_request_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "hold_expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["client_request_id"],
                condition=~models.Q(client_request_id=""),
                name="unique_nonempty_booking_client_request_id",
            ),
        ]

    def __str__(self) -> str:
        """Return the booking confirmation code."""
        return self.confirmation_code

    @property
    def customer_name(self) -> str:
        """Return the current customer display name."""
        if self.user_id and self.user:
            user_name = f"{self.user.first_name} {self.user.last_name}".strip()
            if user_name:
                return user_name
            if self.user.email:
                return self.user.email

        booking_name = f"{self.customer_first_name} {self.customer_last_name}".strip()
        return booking_name or self.customer_email or self.confirmation_code

    @classmethod
    def generate_confirmation_code(cls) -> str:
        """Return a short collision-resistant confirmation code."""
        for _ in range(10):
            code = secrets.token_hex(4).upper()
            if not cls.objects.filter(confirmation_code=code).exists():
                return code
        return uuid.uuid4().hex[:10].upper()


class BookingPayment(models.Model):
    """Mercado Pago-backed payment record for a visit booking."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"
        IN_PROCESS = "in_process", "En proceso"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="payment",
    )
    idempotency_key = models.CharField(max_length=100, unique=True)
    mp_preference_id = models.CharField(max_length=100, blank=True)
    preference_init_point = models.URLField(max_length=1000, blank=True)
    preference_sandbox_init_point = models.URLField(max_length=1000, blank=True)
    mp_payment_id = models.CharField(max_length=100, blank=True)
    mp_merchant_order_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    status_detail = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_type = models.CharField(max_length=50, blank=True)
    installments = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="ARS")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mp_preference_id"],
                condition=~models.Q(mp_preference_id=""),
                name="unique_nonempty_booking_mp_preference_id",
            ),
            models.UniqueConstraint(
                fields=["mp_payment_id"],
                condition=~models.Q(mp_payment_id=""),
                name="unique_nonempty_booking_mp_payment_id",
            ),
        ]

    def __str__(self) -> str:
        """Return a readable booking payment label."""
        return f"{self.booking.confirmation_code} - {self.status}"


class BookingManualRefund(models.Model):
    """Internal record for refunds that staff must execute outside Mercado Pago."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="manual_refund",
    )
    payment = models.ForeignKey(
        BookingPayment,
        on_delete=models.PROTECT,
        related_name="manual_refunds",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="ARS")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=120, default="booking_cancelled")
    note = models.TextField(blank=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="booking_manual_refunds",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a readable refund label."""
        return f"{self.booking.confirmation_code} - {self.status}"
