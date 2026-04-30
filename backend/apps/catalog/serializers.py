"""Catalog serializers."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg
from rest_framework import serializers

from .models import Category, Review, Varietal, Wine, WineImage


class CategorySerializer(serializers.ModelSerializer):
    """Serialize categories."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "icon", "order"]


class VarietalSerializer(serializers.ModelSerializer):
    """Serialize varietals."""

    class Meta:
        model = Varietal
        fields = ["id", "name", "slug", "description", "origin_region"]


class WineImageSerializer(serializers.ModelSerializer):
    """Serialize wine gallery images."""

    class Meta:
        model = WineImage
        fields = ["id", "url", "alt_text", "is_primary", "order"]


class ReviewSerializer(serializers.ModelSerializer):
    """Serialize approved or newly created reviews."""

    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "rating",
            "title",
            "body",
            "user_name",
            "is_verified_purchase",
            "created_at",
        ]
        read_only_fields = ["id", "user_name", "is_verified_purchase", "created_at"]

    def get_user_name(self, obj: Review) -> str:
        """Expose only the reviewer's first name and last initial."""
        return f"{obj.user.first_name} {obj.user.last_name[:1]}."


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for customer review submissions."""

    class Meta:
        model = Review
        fields = ["rating", "title", "body", "order"]


class WineListSerializer(serializers.ModelSerializer):
    """Lightweight wine serializer for grid and list views."""

    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name")
    varietal_name = serializers.CharField(source="varietal.name")
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Wine
        fields = [
            "id",
            "name",
            "slug",
            "vintage_year",
            "price",
            "compare_at_price",
            "discount_percentage",
            "varietal_name",
            "category_name",
            "primary_image",
            "average_rating",
            "review_count",
            "is_in_stock",
            "is_featured",
            "is_limited_edition",
            "alcohol_percentage",
        ]

    def get_primary_image(self, obj: Wine) -> str | None:
        """Return the primary image URL if available."""
        image = obj.images.filter(is_primary=True).first()
        return image.url if image else None

    def get_average_rating(self, obj: Wine) -> float | None:
        """Return the average approved rating rounded to one decimal."""
        result = obj.reviews.filter(is_approved=True).aggregate(avg=Avg("rating"))
        average = result["avg"]
        return round(float(average), 1) if average else None

    def get_review_count(self, obj: Wine) -> int:
        """Return the approved review count."""
        return obj.reviews.filter(is_approved=True).count()

    def get_is_in_stock(self, obj: Wine) -> bool:
        """Return stock availability."""
        return obj.stock > 0

    def get_discount_percentage(self, obj: Wine) -> int | None:
        """Return discount percentage when compare-at price is higher."""
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            discount = ((obj.compare_at_price - obj.price) / obj.compare_at_price) * Decimal("100")
            return int(discount)
        return None


class WineDetailSerializer(WineListSerializer):
    """Detailed wine serializer for PDPs."""

    images = WineImageSerializer(many=True)
    recent_reviews = serializers.SerializerMethodField()
    tasting_profile = serializers.SerializerMethodField()

    class Meta(WineListSerializer.Meta):
        fields = WineListSerializer.Meta.fields + [
            "description",
            "tasting_notes",
            "winemaker_notes",
            "pairing_suggestions",
            "awards",
            "blend_varietals",
            "ageing_months",
            "ageing_type",
            "serving_temperature_min",
            "serving_temperature_max",
            "tasting_profile",
            "images",
            "recent_reviews",
            "stock",
            "sku",
        ]

    def get_recent_reviews(self, obj: Wine) -> list[dict[str, object]]:
        """Return recent approved reviews."""
        reviews = obj.reviews.filter(is_approved=True).order_by("-created_at")[:5]
        return ReviewSerializer(reviews, many=True).data

    def get_tasting_profile(self, obj: Wine) -> dict[str, int]:
        """Return tasting radar profile values."""
        return {
            "tannins": obj.tannins,
            "acidity": obj.acidity,
            "body": obj.body,
            "sweetness": obj.sweetness,
            "fruit_intensity": obj.fruit_intensity,
        }
