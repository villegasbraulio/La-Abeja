"""Views for checkout orders."""

from __future__ import annotations

from typing import cast

import structlog
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import CustomUser

from .access import resolve_guest_order
from .andreani import AndreaniAPIError, AndreaniClient
from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer, ShippingQuoteRequestSerializer
from .state_machine import can_transition

logger = structlog.get_logger(__name__)


class OrderListCreateView(generics.ListCreateAPIView):
    """Create checkout orders and list the authenticated user's orders."""

    permission_classes = [permissions.AllowAny]

    def get_permissions(self):  # type: ignore[override]
        """Allow guest checkout creation while protecting history endpoints."""
        if self.request.method == "POST":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):  # type: ignore[override]
        """Return only the orders belonging to the authenticated user."""
        user = cast(CustomUser, self.request.user)
        return (
            Order.objects.filter(user=user)
            .select_related("user")
            .prefetch_related("items__wine__images")
        )

    def get_serializer_class(self):  # type: ignore[override]
        """Use a write serializer for checkout and read serializer otherwise."""
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Persist a new order and return its full serialized snapshot."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        reused = bool(getattr(serializer, "order_was_reused", False))
        logger.info(
            "order_reused" if reused else "order_created",
            order_id=str(order.id),
            user_id=str(getattr(request.user, "id", "")),
            customer_email=order.customer_email,
        )
        response_serializer = OrderSerializer(order)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK if reused else status.HTTP_201_CREATED,
        )


class OrderDetailView(generics.RetrieveAPIView):
    """Return a single order for the authenticated user."""

    permission_classes = [permissions.AllowAny]
    serializer_class = OrderSerializer

    def get_object(self):  # type: ignore[override]
        """Allow authenticated owners or guests with a signed access token."""
        if self.request.user.is_authenticated:
            user = cast(CustomUser, self.request.user)
            return get_object_or_404(
                Order.objects.filter(user=user)
                .select_related("user")
                .prefetch_related("items__wine__images"),
                pk=self.kwargs["pk"],
            )

        guest_order = resolve_guest_order(
            order_id=str(self.kwargs["pk"]),
            guest_access_token=self.request.query_params.get("guest_access_token"),
        )
        if guest_order is None:
            raise Http404("Order not found")
        return guest_order


class ShippingQuoteView(APIView):
    """Quote shipping methods for the current cart and destination."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Return backend-calculated shipping options for checkout."""
        serializer = ShippingQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "quotes": serializer.get_quotes(),
            }
        )


class AndreaniLocalityListView(APIView):
    """Expose normalized Andreani localities through the backend cache."""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request) -> Response:
        """Return cached locality master data."""
        _ = request
        try:
            return Response(AndreaniClient().get_localities())
        except AndreaniAPIError as exc:
            logger.error("andreani_localities_failed", error=str(exc))
            return Response(
                {"detail": "No pudimos consultar las localidades de Andreani."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class AndreaniBranchListView(APIView):
    """Expose Andreani branches through the backend cache."""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request) -> Response:
        """Return cached branch master data."""
        _ = request
        try:
            return Response(AndreaniClient().get_branches())
        except AndreaniAPIError as exc:
            logger.error("andreani_branches_failed", error=str(exc))
            return Response(
                {"detail": "No pudimos consultar las sucursales de Andreani."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class OrderCancelView(APIView):
    """Allow a customer to cancel eligible orders."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, pk: str) -> Response:
        """Cancel orders that have not yet been paid or fulfilled."""
        order = self._get_order(request, pk)
        if not can_transition(order.status, Order.Status.CANCELLED):
            return Response(
                {"detail": "Este pedido ya no puede cancelarse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        logger.info(
            "order_cancelled",
            order_id=str(order.id),
            user_id=str(getattr(request.user, "id", "")),
            customer_email=order.customer_email,
        )
        return Response(OrderSerializer(order).data)

    def _get_order(self, request: Request, pk: str) -> Order:
        """Return the authenticated order or a guest order with a valid token."""
        if request.user.is_authenticated:
            user = cast(CustomUser, request.user)
            return get_object_or_404(
                Order.objects.filter(user=user).select_related("user"),
                pk=pk,
            )

        guest_order = resolve_guest_order(
            order_id=pk,
            guest_access_token=request.query_params.get("guest_access_token"),
        )
        if guest_order is None:
            raise Http404("Order not found")
        return guest_order
