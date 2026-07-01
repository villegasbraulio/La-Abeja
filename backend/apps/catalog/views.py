"""Catalog API views."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework import generics, permissions

from .models import Category, Review, Varietal, Wine
from .serializers import (
    CategorySerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    VarietalSerializer,
    WineDetailSerializer,
    WineListSerializer,
)


def _int_param(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _decimal_param(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


class WineListView(generics.ListAPIView):
    """List active wines with filtering."""

    serializer_class = WineListSerializer
    ordering_fields = ["price", "name", "vintage_year"]

    def get_queryset(self):  # type: ignore[override]
        """Build the list queryset with eager loading."""
        queryset = (
            Wine.objects.filter(is_active=True)
            .select_related("category", "varietal")
            .prefetch_related("images", "reviews")
        )
        params = self.request.query_params

        if category := params.get("category"):
            queryset = queryset.filter(category__slug=category)
        if varietal := params.get("varietal"):
            queryset = queryset.filter(varietal__slug=varietal)
        if vintage_year := _int_param(params.get("vintage_year")):
            queryset = queryset.filter(vintage_year=vintage_year)
        if vintage_min := _int_param(params.get("vintage_min")):
            queryset = queryset.filter(vintage_year__gte=vintage_min)
        if vintage_max := _int_param(params.get("vintage_max")):
            queryset = queryset.filter(vintage_year__lte=vintage_max)
        if min_price := _decimal_param(params.get("min_price")):
            queryset = queryset.filter(price__gte=min_price)
        if max_price := _decimal_param(params.get("max_price")):
            queryset = queryset.filter(price__lte=max_price)
        if params.get("in_stock") == "true":
            queryset = queryset.filter(stock__gt=0)
        if params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)
        if search := params.get("search"):
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(varietal__name__icontains=search)
            )

        return queryset


class WineDetailView(generics.RetrieveAPIView):
    """Retrieve a wine by slug."""

    serializer_class = WineDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):  # type: ignore[override]
        """Build the detail queryset with eager loading."""
        return (
            Wine.objects.filter(is_active=True)
            .select_related("category", "varietal")
            .prefetch_related("images", "reviews__user")
        )


class FeaturedWineListView(generics.ListAPIView):
    """Return featured active wines."""

    serializer_class = WineListSerializer
    pagination_class = None

    def get_queryset(self):  # type: ignore[override]
        """Build the featured wine queryset."""
        return (
            Wine.objects.filter(is_active=True, is_featured=True)
            .select_related("category", "varietal")
            .prefetch_related("images", "reviews")
        )


class CategoryListView(generics.ListAPIView):
    """Return product categories."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class VarietalListView(generics.ListAPIView):
    """Return grape varietals."""

    serializer_class = VarietalSerializer
    queryset = Varietal.objects.all()
    pagination_class = None


class WineReviewListCreateView(generics.ListCreateAPIView):
    """List approved reviews and allow authenticated submissions."""

    lookup_url_kwarg = "slug"

    def get_permissions(self) -> list[permissions.BasePermission]:
        """Allow anonymous review browsing while protecting creation."""
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):  # type: ignore[override]
        """Use a dedicated serializer for write operations."""
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_queryset(self):  # type: ignore[override]
        """Return approved reviews for the targeted wine."""
        return Review.objects.filter(
            wine__slug=self.kwargs["slug"],
            is_approved=True,
        ).select_related("user")

    def perform_create(self, serializer: ReviewCreateSerializer) -> None:
        """Attach the authenticated user and target wine to the new review."""
        wine = generics.get_object_or_404(
            Wine.objects.filter(is_active=True),
            slug=self.kwargs["slug"],
        )
        serializer.save(user=self.request.user, wine=wine)
