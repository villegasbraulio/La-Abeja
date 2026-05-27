"""Integration tests for payment endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.catalog.tests.factories import WineFactory
from apps.orders.tests.factories import OrderFactory, OrderItemFactory

from .factories import PaymentFactory


@pytest.mark.django_db
class TestPaymentEndpoints:
    """Coverage for Checkout Pro preference and webhook flows."""

    @patch("apps.payments.serializers.MercadoPagoClient.create_preference")
    def test_create_preference_creates_payment_record(
        self,
        mock_create_preference,
        authenticated_client,
        settings,
    ) -> None:
        """The payment endpoint should create or update the payment record."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        client, user = authenticated_client
        order = OrderFactory(user=user, status="pending_payment", total=Decimal("9800.00"))
        OrderItemFactory(order=order)
        mock_create_preference.return_value = {
            "id": "pref_123",
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref_123",
            "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/v1/redirect?pref_id=pref_123",
        }

        response = client.post(
            "/api/v1/payments/create-preference/",
            {"order_id": str(order.id)},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["preference_id"] == "pref_123"
        assert order.payment.mp_preference_id == "pref_123"

    @patch("apps.payments.views.MercadoPagoClient.get_payment")
    def test_webhook_approves_payment_and_order(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """A payment webhook should sync both payment and order state."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        wine = WineFactory(stock=10)
        order = OrderFactory(status="pending_payment", total=Decimal("8000.00"))
        OrderItemFactory(order=order, wine=wine, quantity=2, subtotal=Decimal("9000.00"))
        payment = PaymentFactory(order=order, amount=order.total, status="pending")
        mock_get_payment.return_value = {
            "id": 99887766,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(order.id),
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
            "installments": 3,
            "order": {"id": "merchant_order_1"},
        }

        response = api_client.post(
            "/api/v1/payments/webhook/?data.id=99887766&type=payment",
            {"id": 12345, "type": "payment", "data": {"id": "99887766"}},
            format="json",
        )

        payment.refresh_from_db()
        order.refresh_from_db()
        wine.refresh_from_db()

        assert response.status_code == 200
        assert payment.status == "approved"
        assert payment.mp_payment_id == "99887766"
        assert order.status == "paid"
        assert wine.stock == 8

    @patch("apps.payments.serializers.MercadoPagoClient.create_preference")
    def test_create_preference_rejects_ineligible_order(
        self,
        mock_create_preference,
        authenticated_client,
    ) -> None:
        """Paid orders cannot generate a new checkout preference."""
        client, user = authenticated_client
        order = OrderFactory(user=user, status="paid")
        OrderItemFactory(order=order)

        response = client.post(
            "/api/v1/payments/create-preference/",
            {"order_id": str(order.id)},
            format="json",
        )

        assert response.status_code == 400
        assert "order_id" in response.data
        mock_create_preference.assert_not_called()
