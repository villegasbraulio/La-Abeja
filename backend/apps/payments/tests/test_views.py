"""Integration tests for payment endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.catalog.tests.factories import WineFactory
from apps.orders.access import build_guest_access_token
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory, OrderItemFactory

from ..models import Payment, PaymentWebhookLog
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

        repeated_response = client.post(
            "/api/v1/payments/create-preference/",
            {"order_id": str(order.id)},
            format="json",
        )

        assert repeated_response.status_code == 201
        assert repeated_response.data["preference_id"] == "pref_123"
        assert mock_create_preference.call_count == 1

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
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        wine = WineFactory(stock=10)
        order = OrderFactory(status="pending_payment", total=Decimal("8000.00"))
        OrderItemFactory(order=order, wine=wine, quantity=2, subtotal=Decimal("9000.00"))
        payment = PaymentFactory(order=order, amount=order.total, status="pending")
        mock_get_payment.return_value = {
            "id": 99887766,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(order.id),
            "transaction_amount": "8000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
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

        repeated_response = api_client.post(
            "/api/v1/payments/webhook/?data.id=99887766&type=payment",
            {"id": 12345, "type": "payment", "data": {"id": "99887766"}},
            format="json",
        )
        wine.refresh_from_db()

        assert repeated_response.status_code == 200
        assert wine.stock == 8
        assert mock_get_payment.call_count == 1
        assert PaymentWebhookLog.objects.filter(mp_notification_id="12345").count() == 1

        distinct_notification_response = api_client.post(
            "/api/v1/payments/webhook/?data.id=99887766&type=payment",
            {"id": 12346, "type": "payment", "data": {"id": "99887766"}},
            format="json",
        )
        wine.refresh_from_db()

        assert distinct_notification_response.status_code == 200
        assert wine.stock == 8
        assert mock_get_payment.call_count == 2

    @patch("apps.payments.views.MercadoPagoClient.get_payment")
    def test_webhook_does_not_approve_payment_with_integrity_mismatch(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """A forged or misrouted approved payment must not approve the order."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        order = OrderFactory(status="pending_payment", total=Decimal("8000.00"))
        OrderItemFactory(order=order)
        payment = PaymentFactory(order=order, amount=order.total, status="pending")
        mock_get_payment.return_value = {
            "id": 99887767,
            "status": "approved",
            "external_reference": str(order.id),
            "transaction_amount": "1.00",
            "currency_id": "ARS",
            "collector_id": 445566,
        }

        response = api_client.post(
            "/api/v1/payments/webhook/?data.id=99887767&type=payment",
            {"id": 12347, "type": "payment", "data": {"id": "99887767"}},
            format="json",
        )

        payment.refresh_from_db()
        order.refresh_from_db()
        webhook = PaymentWebhookLog.objects.get(mp_notification_id="12347")
        assert response.status_code == 200
        assert payment.status == Payment.Status.PENDING
        assert order.status == Order.Status.PENDING_PAYMENT
        assert "transaction_amount" in webhook.error

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

    @patch("apps.payments.serializers.MercadoPagoClient.create_preference")
    def test_guest_can_create_preference_with_signed_token(
        self,
        mock_create_preference,
        api_client,
        settings,
    ) -> None:
        """Guest orders can generate a checkout preference with the signed token."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        order = OrderFactory(
            user=None,
            customer_email="guest@example.com",
            status="pending_payment",
        )
        OrderItemFactory(order=order)
        mock_create_preference.return_value = {
            "id": "pref_guest_123",
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref_guest_123",
            "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/v1/redirect?pref_id=pref_guest_123",
        }

        response = api_client.post(
            "/api/v1/payments/create-preference/",
            {
                "order_id": str(order.id),
                "guest_access_token": build_guest_access_token(order),
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["preference_id"] == "pref_guest_123"
