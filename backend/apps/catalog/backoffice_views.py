"""Views for the custom backoffice API."""

from __future__ import annotations

import csv
from datetime import timedelta
from typing import cast

import structlog
from django.db.models import Count, F, Max, Q, QuerySet, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import filters, generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models import AgentRun
from apps.ai.tools.analytics_tools import (
    get_conversion_funnel,
    get_margin_estimate_by_product,
    get_repeat_customers_metrics,
    get_returns_and_incidents_metrics,
    get_sales_by_bottle,
    get_sales_by_channel,
    get_sales_by_varietal,
    get_sales_over_period,
    get_sales_summary,
)
from apps.ai.tools.base import ToolContext
from apps.authentication.models import CustomUser
from apps.authentication.permissions import IsStaffUser
from apps.orders.models import Order, PromoCode

from .backoffice_serializers import (
    BackofficeCategorySerializer,
    BackofficeCustomerSerializer,
    BackofficeDashboardSerializer,
    BackofficeOrderActionSerializer,
    BackofficeOrderDetailSerializer,
    BackofficeOrderListSerializer,
    BackofficePromoCodeSerializer,
    BackofficeVarietalSerializer,
    BackofficeWineDetailSerializer,
    BackofficeWineListSerializer,
)
from .models import Category, Varietal, Wine

logger = structlog.get_logger(__name__)


class BackofficeSalesMetricsView(APIView):
    """Return a complete sales dashboard without coupling the UI to the copilot."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Aggregate sales, customer, product, channel, and funnel indicators."""
        period = str(request.query_params.get("period") or "last_30_days")
        grain = str(request.query_params.get("grain") or "day")
        payload: dict[str, object] = {"period": period, "grain": grain, "limit": 10}

        if period == "current_year":
            today = timezone.localdate()
            payload.update(
                start_date=today.replace(month=1, day=1).isoformat(),
                end_date=today.isoformat(),
                grain="month",
            )
        elif period == "last_12_months":
            today = timezone.localdate()
            payload.update(
                start_date=(today - timedelta(days=365)).isoformat(),
                end_date=today.isoformat(),
                grain="month",
            )

        context = ToolContext(
            run=cast(AgentRun, None),
            user_id=request.user.id,
            is_staff=True,
        )
        return Response(
            {
                "summary": get_sales_summary(payload, context),
                "timeline": get_sales_over_period(payload, context),
                "by_varietal": get_sales_by_varietal(payload, context),
                "by_product": get_sales_by_bottle(payload, context),
                "by_channel": get_sales_by_channel(payload, context),
                "margins": get_margin_estimate_by_product(payload, context),
                "repeat_customers": get_repeat_customers_metrics(payload, context),
                "funnel": get_conversion_funnel(payload, context),
                "incidents": get_returns_and_incidents_metrics(payload, context),
            }
        )


class BackofficeDashboardView(APIView):
    """Return operational summary cards for the custom backoffice."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Serialize high-level KPIs for the internal panel."""
        paid_without_tracking = Order.objects.filter(
            status__in=[Order.Status.PAID, Order.Status.PREPARING, Order.Status.READY_TO_SHIP],
            tracking_number="",
        ).count()
        payment_failed = Order.objects.filter(status=Order.Status.PAYMENT_FAILED).count()
        ready_to_ship = Order.objects.filter(status=Order.Status.READY_TO_SHIP).count()
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
            "action_items": [
                {
                    "label": "Pedidos pagados sin tracking",
                    "count": paid_without_tracking,
                    "href": "/backoffice/pedidos",
                },
                {
                    "label": "Pagos fallidos para contactar",
                    "count": payment_failed,
                    "href": "/backoffice/pedidos",
                },
                {
                    "label": "Pedidos listos para enviar",
                    "count": ready_to_ship,
                    "href": "/backoffice/pedidos",
                },
                {
                    "label": "Vinos con stock bajo",
                    "count": Wine.objects.filter(
                        is_active=True,
                        stock__lte=F("low_stock_threshold"),
                    ).count(),
                    "href": "/backoffice/vinos",
                },
            ],
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


class BackofficeOrderListView(generics.ListAPIView):
    """List orders for the custom backoffice queue."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeOrderListSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["created_at", "total", "status"]
    ordering = ["-created_at"]
    search_fields = ["order_number", "user__email", "user__first_name", "user__last_name"]

    def get_queryset(self) -> QuerySet[Order]:
        """Return orders with staff-friendly filters."""
        queryset = (
            Order.objects.select_related("user", "payment")
            .prefetch_related("items")
            .all()
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class BackofficeOrderDetailView(generics.RetrieveAPIView):
    """Retrieve a single order for internal operations."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeOrderDetailSerializer
    queryset = (
        Order.objects.select_related("user", "payment")
        .prefetch_related("items__wine__images")
        .all()
    )


class BackofficeOrderActionView(generics.GenericAPIView):
    """Update the operational fields staff needs day to day."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficeOrderActionSerializer
    queryset = (
        Order.objects.select_related("user", "payment")
        .prefetch_related("items__wine__images")
        .all()
    )

    def patch(self, request: Request, pk: str) -> Response:
        """Apply a status/tracking/note update and return the refreshed order."""
        order = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(BackofficeOrderDetailSerializer(order).data)


class BackofficePromoCodeListCreateView(generics.ListCreateAPIView):
    """List and create promo codes."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficePromoCodeSerializer
    queryset = PromoCode.objects.all().order_by("-valid_until", "code")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code"]
    ordering_fields = ["code", "valid_until", "used_count", "is_active"]


class BackofficePromoCodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a promo code."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = BackofficePromoCodeSerializer
    queryset = PromoCode.objects.all()


class BackofficeCustomerListView(APIView):
    """List registered and guest customers with basic buying history."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> Response:
        """Return a paginated-shape customer list for the frontend table."""
        search = str(request.query_params.get("search") or "").strip().lower()
        registered = (
            CustomUser.objects.filter(is_staff=False)
            .annotate(
                orders_count=Count("orders", distinct=True),
                total_spent=Sum("orders__total", filter=Q(orders__status=Order.Status.DELIVERED)),
                last_order_at=Max("orders__created_at"),
            )
        )
        if search:
            registered = registered.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
            )

        rows = list(BackofficeCustomerSerializer(registered, many=True).data)
        registered_emails = {row["email"] for row in rows}
        guests = (
            Order.objects.filter(user__isnull=True)
            .exclude(customer_email="")
            .values("customer_email")
            .annotate(
                orders_count=Count("id"),
                total_spent=Sum("total", filter=Q(status=Order.Status.DELIVERED)),
                last_order_at=Max("created_at"),
            )
        )
        if search:
            guests = guests.filter(customer_email__icontains=search)

        for guest in guests:
            email = str(guest["customer_email"])
            if email in registered_emails:
                continue
            rows.append(
                {
                    "id": f"guest:{email}",
                    "email": email,
                    "full_name": email,
                    "phone": "",
                    "newsletter_subscribed": False,
                    "orders_count": guest["orders_count"],
                    "total_spent": guest["total_spent"],
                    "last_order_at": guest["last_order_at"],
                    "date_joined": guest["last_order_at"],
                }
            )

        rows.sort(key=lambda row: str(row.get("last_order_at") or row.get("date_joined") or ""), reverse=True)
        return Response({"count": len(rows), "next": None, "previous": None, "results": rows})


class BackofficeOrderExportView(APIView):
    """Export orders as CSV."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> HttpResponse:
        """Return a compact order export for operations."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="pedidos.csv"'
        writer = csv.writer(response)
        writer.writerow(["pedido", "cliente", "email", "estado", "total", "tracking", "creado"])
        for order in Order.objects.select_related("user").order_by("-created_at"):
            customer_name = BackofficeOrderListSerializer().get_customer_name(order)
            customer_email = BackofficeOrderListSerializer().get_customer_email(order)
            writer.writerow(
                [
                    order.order_number,
                    customer_name,
                    customer_email,
                    order.get_status_display(),
                    order.total,
                    order.tracking_number,
                    order.created_at.isoformat(),
                ]
            )
        return response


class BackofficeCustomerExportView(APIView):
    """Export customers as CSV."""

    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request: Request) -> HttpResponse:
        """Return a compact customer export."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="clientes.csv"'
        writer = csv.writer(response)
        writer.writerow(["nombre", "email", "telefono", "newsletter", "alta"])
        seen_emails = set()
        for user in CustomUser.objects.filter(is_staff=False).order_by("-date_joined"):
            seen_emails.add(user.email)
            writer.writerow(
                [
                    user.full_name,
                    user.email,
                    user.phone,
                    "si" if user.newsletter_subscribed else "no",
                    user.date_joined.isoformat(),
                ]
            )
        guests = (
            Order.objects.filter(user__isnull=True)
            .exclude(customer_email="")
            .values("customer_email")
            .annotate(last_order_at=Max("created_at"))
            .order_by("-last_order_at")
        )
        for guest in guests:
            email = str(guest["customer_email"])
            if email in seen_emails:
                continue
            writer.writerow(["", email, "", "no", guest["last_order_at"].isoformat()])
        return response
