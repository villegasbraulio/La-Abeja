"""Reservation models."""

from __future__ import annotations

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
    cancellation_hours = models.IntegerField(default=48)
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
    )
    time_slot = models.ForeignKey(TimeSlot, related_name="bookings", on_delete=models.PROTECT)
    guest_count = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    special_requests = models.TextField(blank=True)
    dietary_restrictions = models.JSONField(default=list, blank=True)
    qr_code_url = models.URLField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return the booking confirmation code."""
        return self.confirmation_code
