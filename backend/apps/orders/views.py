"""Views for checkout orders."""

from __future__ import annotations

from typing import cast

import structlog
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import CustomUser

from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer, ShippingQuoteRequestSerializer
from .state_machine import can_transition

logger = structlog.get_logger(__name__)


class OrderListCreateView(generics.ListCreateAPIView):
    """Create checkout orders and list the authenticated user's orders."""

    permission_classes = [permissions.IsAuthenticated]

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
        logger.info("order_created", order_id=str(order.id), user_id=str(request.user.id))
        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    """Return a single order for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):  # type: ignore[override]
        """Restrict lookup to the current user's orders."""
        user = cast(CustomUser, self.request.user)
        return (
            Order.objects.filter(user=user)
            .select_related("user")
            .prefetch_related("items__wine__images")
        )


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


class OrderCancelView(APIView):
    """Allow a customer to cancel eligible orders."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        """Cancel orders that have not yet been paid or fulfilled."""
        user = cast(CustomUser, request.user)
        order = get_object_or_404(
            Order.objects.filter(user=user).select_related("user"),
            pk=pk,
        )
        if not can_transition(order.status, Order.Status.CANCELLED):
            return Response(
                {"detail": "Este pedido ya no puede cancelarse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        logger.info("order_cancelled", order_id=str(order.id), user_id=str(user.id))
        return Response(OrderSerializer(order).data)
