"""Catalog models."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    """Product category for the catalog."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        """Return the category name."""
        return self.name


class Varietal(models.Model):
    """Primary grape varietal."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    origin_region = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        """Return the varietal name."""
        return self.name


class Wine(models.Model):
    """Sellable wine product."""

    class AgeingType(models.TextChoices):
        OAK = "oak", "Roble"
        STAINLESS = "stainless", "Acero Inoxidable"
        CEMENT = "cement", "Hormigón"
        AMPHORA = "amphora", "Ánfora"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    varietal = models.ForeignKey(Varietal, on_delete=models.PROTECT)
    blend_varietals = models.JSONField(default=list, blank=True)
    vintage_year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    sku = models.CharField(max_length=50, unique=True)
    alcohol_percentage = models.DecimalField(max_digits=4, decimal_places=1)
    serving_temperature_min = models.IntegerField()
    serving_temperature_max = models.IntegerField()
    ageing_months = models.IntegerField(default=0)
    ageing_type = models.CharField(max_length=20, choices=AgeingType.choices)
    tannins = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    acidity = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    body = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    sweetness = models.IntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fruit_intensity = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    description = models.TextField()
    tasting_notes = models.TextField()
    pairing_suggestions = models.JSONField(default=list, blank=True)
    winemaker_notes = models.TextField(blank=True)
    awards = models.JSONField(default=list, blank=True)
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_limited_edition = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["varietal", "vintage_year"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self) -> str:
        """Return the product display name."""
        return self.name


class WineImage(models.Model):
    """Image assets for a wine."""

    wine = models.ForeignKey(Wine, related_name="images", on_delete=models.CASCADE)
    url = models.URLField()
    alt_text = models.CharField(max_length=200)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-is_primary", "id"]

    def __str__(self) -> str:
        """Return a useful image label."""
        return f"{self.wine.name} image {self.order}"


class Review(models.Model):
    """Customer review for a wine."""

    wine = models.ForeignKey(Wine, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["wine", "user", "order"],
                name="unique_review_per_order",
            )
        ]

    def __str__(self) -> str:
        """Return a concise review identifier."""
        return f"{self.wine.name} - {self.user.email}"
