"""Views for the custom backoffice API."""

from __future__ import annotations

import structlog
from django.db.models import Count, F, QuerySet
from rest_framework import filters, generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsStaffUser
from apps.orders.models import Order

from .backoffice_serializers import (
    BackofficeCategorySerializer,
    BackofficeDashboardSerializer,
    BackofficeVarietalSerializer,
    BackofficeWineDetailSerializer,
    BackofficeWineListSerializer,
)
from .models import Category, Varietal, Wine

logger = structlog.get_logger(__name__)

class BackofficeDashboardView(APIView):
    """Return operational summary cards for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Serialize high-level KPIs for the internal panel."""
        payload = {
            "total_wines": Wine.objects.count(),
            "active_wines": Wine.objects.filter(is_active=True).count(),
            "featured_wines": Wine.objects.filter(is_featured=True, is_active=True).count(),
            "low_stock_wines": Wine.objects.filter(
                is_active=True,
                stock__lte=F("low_stock_threshold"),
            ).count(),
            "categories": Category.objects.count(),
            "varietals": Varietal.objects.count(),
            "total_orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(
                status__in=[Order.Status.PENDING_PAYMENT, Order.Status.PREPARING]
            ).count(),
            "low_stock_items": list(
                Wine.objects.filter(is_active=True, stock__lte=F("low_stock_threshold"))
                .values("id", "name", "stock", "low_stock_threshold")[:5]
            ),
        }
        serializer = BackofficeDashboardSerializer(payload)
        return Response(serializer.data)


class BackofficeCategoryListCreateView(generics.ListCreateAPIView):
    """List and create catalog categories for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeCategorySerializer
    queryset = Category.objects.all().annotate(wines_count=Count("wine"))
    pagination_class = None
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["order", "name"]
    ordering = ["order", "name"]
    search_fields = ["name", "slug"]

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Create a category and log failures explicitly."""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_category_create_failed", error=str(exc))
            raise


class BackofficeCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a category."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeCategorySerializer
    queryset = Category.objects.all().annotate(wines_count=Count("wine"))

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Update a category with structured error logging."""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_category_update_failed", error=str(exc))
            raise

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Delete a category with structured error logging."""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_category_delete_failed", error=str(exc))
            raise


class BackofficeVarietalListCreateView(generics.ListCreateAPIView):
    """List and create varietals for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeVarietalSerializer
    queryset = Varietal.objects.all().annotate(wines_count=Count("wine"))
    pagination_class = None
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["name"]
    ordering = ["name"]
    search_fields = ["name", "slug", "origin_region"]

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Create a varietal and log failures explicitly."""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_varietal_create_failed", error=str(exc))
            raise


class BackofficeVarietalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a varietal."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeVarietalSerializer
    queryset = Varietal.objects.all().annotate(wines_count=Count("wine"))

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Update a varietal with structured error logging."""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_varietal_update_failed", error=str(exc))
            raise

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Delete a varietal with structured error logging."""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_varietal_delete_failed", error=str(exc))
            raise


class BackofficeWineListCreateView(generics.ListCreateAPIView):
    """List and create wines for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["name", "price", "stock", "updated_at", "vintage_year"]
    ordering = ["-is_featured", "name"]
    search_fields = ["name", "sku", "slug", "varietal__name", "category__name"]

    def get_queryset(self) -> QuerySet[Wine]:
        """Return the filtered wine queryset for the current action."""
        queryset = (
            Wine.objects.select_related("category", "varietal")
            .prefetch_related("images")
            .all()
        )
        category = self.request.query_params.get("category")
        varietal = self.request.query_params.get("varietal")
        is_active = self.request.query_params.get("is_active")
        if category:
            queryset = queryset.filter(category_id=category)
        if varietal:
            queryset = queryset.filter(varietal_id=varietal)
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset

    def get_serializer_class(self):  # type: ignore[override]
        """Use a lightweight serializer for lists and a full serializer for writes."""
        if self.request.method == "GET":
            return BackofficeWineListSerializer
        return BackofficeWineDetailSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Create a wine and log failures explicitly."""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_wine_create_failed", error=str(exc))
            raise


class BackofficeWineDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a wine."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeWineDetailSerializer
    queryset = Wine.objects.select_related("category", "varietal").prefetch_related("images")

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Update a wine with structured error logging."""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_wine_update_failed", error=str(exc))
            raise

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Delete a wine with structured error logging."""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("backoffice_wine_delete_failed", error=str(exc))
            raise

    def delete(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Return a more explicit delete response for the frontend."""
        self.destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)
