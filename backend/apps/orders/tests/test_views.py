"""Integration tests for order endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.catalog.tests.factories import WineFactory
from apps.orders.access import build_guest_access_token

from .factories import OrderFactory, OrderItemFactory


@pytest.mark.django_db
class TestOrderCheckoutEndpoints:
    """Coverage for order creation and retrieval."""

    def test_checkout_can_quote_shipping_options(self, api_client) -> None:
        """Shipping options should come from the backend quote endpoint."""
        first_wine = WineFactory(price=Decimal("4500.00"), stock=10)
        second_wine = WineFactory(price=Decimal("6200.00"), stock=8)

        response = api_client.post(
            "/api/v1/orders/shipping-quotes/",
            {
                "items": [
                    {"wine_id": str(first_wine.id), "quantity": 2},
                    {"wine_id": str(second_wine.id), "quantity": 1},
                ],
                "shipping_address": {
                    "city": "San Rafael",
                    "province": "Mendoza",
                    "postal_code": "5600",
                    "country": "Argentina",
                },
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.data["quotes"]) == 3
        assert response.data["quotes"][0]["shipping_method"] == "standard"
        assert response.data["quotes"][0]["shipping_cost"] == "3993.60"
        assert response.data["quotes"][0]["provider"] == "andreani"
        assert response.data["quotes"][1]["shipping_method"] == "express"
        assert response.data["quotes"][1]["shipping_cost"] == "6336.00"
        assert response.data["quotes"][2]["shipping_method"] == "pickup"
        assert response.data["quotes"][2]["shipping_cost"] == "0.00"

    @patch("apps.orders.serializers.EmailService.send_transactional")
    def test_authenticated_user_can_create_order(
        self,
        mock_send_transactional,
        authenticated_client,
    ) -> None:
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
        assert response.data["shipping_cost"] == "6336.00"
        assert response.data["total"] == "21536.00"
        assert response.data["shipping_quote"]["provider"] == "andreani"
        assert response.data["shipping_quote"]["service_level"] == "express"
        assert response.data["customer_email"]
        assert len(response.data["items"]) == 2
        mock_send_transactional.assert_called_once()

    @patch("apps.orders.serializers.EmailService.send_transactional")
    def test_guest_checkout_can_create_order(
        self,
        mock_send_transactional,
        api_client,
    ) -> None:
        """Guests should be able to create an order without registering."""
        first_wine = WineFactory(price=Decimal("4500.00"), stock=10)

        response = api_client.post(
            "/api/v1/orders/orders/",
            {
                "items": [
                    {"wine_id": str(first_wine.id), "quantity": 2},
                ],
                "shipping_method": "standard",
                "customer_email": "guest@example.com",
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

        assert response.status_code == 201
        assert response.data["customer_email"] == "guest@example.com"
        assert response.data["guest_access_token"]
        mock_send_transactional.assert_called_once()

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

    def test_guest_can_read_and_cancel_order_with_signed_token(self, api_client) -> None:
        """Guests should manage their order with the signed guest token."""
        order = OrderFactory(
            user=None,
            customer_email="guest@example.com",
            status="pending_payment",
        )
        OrderItemFactory(order=order)
        token = build_guest_access_token(order)

        detail_response = api_client.get(
            f"/api/v1/orders/orders/{order.id}/",
            {"guest_access_token": token},
            format="json",
        )
        cancel_response = api_client.post(
            f"/api/v1/orders/orders/{order.id}/cancel/?guest_access_token={token}",
            format="json",
        )

        assert detail_response.status_code == 200
        assert detail_response.data["customer_email"] == "guest@example.com"
        assert cancel_response.status_code == 200
        assert cancel_response.data["status"] == "cancelled"
