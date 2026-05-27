"""Integration tests for order endpoints."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.catalog.tests.factories import WineFactory

from .factories import OrderFactory, OrderItemFactory


@pytest.mark.django_db
class TestOrderCheckoutEndpoints:
    """Coverage for order creation and retrieval."""

    def test_authenticated_user_can_create_order(self, authenticated_client) -> None:
        """Checkout should create an order from local cart items."""
        client, _ = authenticated_client
        first_wine = WineFactory(price=Decimal("4500.00"), stock=10)
        second_wine = WineFactory(price=Decimal("6200.00"), stock=8)

        response = client.post(
            "/api/v1/orders/orders/",
            {
                "items": [
                    {"wine_id": str(first_wine.id), "quantity": 2},
                    {"wine_id": str(second_wine.id), "quantity": 1},
                ],
                "shipping_method": "express",
                "shipping_address": {
                    "recipient_name": "Maria Perez",
                    "street": "Av. San Martin",
                    "number": "450",
                    "floor_apt": "2B",
                    "city": "San Rafael",
                    "province": "Mendoza",
                    "postal_code": "5600",
                    "country": "Argentina",
                    "phone": "+5492604555555",
                },
                "notes": "Entregar por la tarde.",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == "pending_payment"
        assert response.data["shipping_cost"] == "6500.00"
        assert response.data["total"] == "21700.00"
        assert len(response.data["items"]) == 2

    def test_checkout_rejects_insufficient_stock(self, authenticated_client) -> None:
        """Checkout should fail when the requested quantity exceeds stock."""
        client, _ = authenticated_client
        wine = WineFactory(stock=1)

        response = client.post(
            "/api/v1/orders/orders/",
            {
                "items": [{"wine_id": str(wine.id), "quantity": 3}],
                "shipping_method": "standard",
                "shipping_address": {
                    "recipient_name": "Maria Perez",
                    "street": "Av. San Martin",
                    "number": "450",
                    "city": "San Rafael",
                    "province": "Mendoza",
                    "postal_code": "5600",
                    "country": "Argentina",
                    "phone": "+5492604555555",
                },
            },
            format="json",
        )

        assert response.status_code == 400
        assert "items" in response.data

    def test_order_list_returns_only_current_user_orders(self, authenticated_client) -> None:
        """A user should only see their own order history."""
        client, user = authenticated_client
        own_order = OrderFactory(user=user)
        OrderItemFactory(order=own_order)
        other_order = OrderFactory()
        OrderItemFactory(order=other_order)

        response = client.get("/api/v1/orders/orders/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(own_order.id)

    def test_user_can_cancel_pending_order(self, authenticated_client) -> None:
        """Pending orders can be cancelled by their owner."""
        client, user = authenticated_client
        order = OrderFactory(user=user, status="pending_payment")
        OrderItemFactory(order=order)

        response = client.post(f"/api/v1/orders/orders/{order.id}/cancel/")

        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_paid_order_cannot_be_cancelled(self, authenticated_client) -> None:
        """Paid orders should not be cancellable from the storefront."""
        client, user = authenticated_client
        order = OrderFactory(user=user, status="paid")
        OrderItemFactory(order=order)

        response = client.post(f"/api/v1/orders/orders/{order.id}/cancel/")

        assert response.status_code == 400
        assert response.data["detail"] == "Este pedido ya no puede cancelarse."
