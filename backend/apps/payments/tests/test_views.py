"""Integration tests for payment endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.catalog.tests.factories import WineFactory
from apps.orders.access import build_guest_access_token
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory, OrderItemFactory

from ..mercadopago import MercadoPagoAPIError
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
        assert order.status == "preparing"
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

    @patch("apps.payments.views.MercadoPagoClient.get_payment")
    def test_webhook_simulation_with_fake_data_id_returns_200(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """Mercado Pago simulation payloads should not fail when the payment does not exist."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        mock_get_payment.side_effect = MercadoPagoAPIError("payment not found")

        response = api_client.post(
            "/api/v1/payments/webhook/?data.id=123456&type=payment",
            {
                "action": "payment.updated",
                "api_version": "v1",
                "data": {"id": "123456"},
                "date_created": "2021-11-01T02:02:02Z",
                "id": "123456",
                "live_mode": False,
                "type": "payment",
                "user_id": 724484980,
            },
            format="json",
        )

        webhook = PaymentWebhookLog.objects.get(mp_notification_id="123456")

        assert response.status_code == 200
        assert webhook.processed is True
        assert webhook.error == "payment not found"

    @patch("apps.payments.views.MercadoPagoClient.get_payment")
    def test_webhook_keeps_pickup_orders_as_paid(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """Pickup orders stay paid because they do not enter carrier preparation."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        order = OrderFactory(
            status="pending_payment",
            total=Decimal("8000.00"),
            shipping_method=Order.ShippingMethod.PICKUP,
        )
        OrderItemFactory(order=order)
        payment = PaymentFactory(order=order, amount=order.total, status="pending")
        mock_get_payment.return_value = {
            "id": 99887769,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(order.id),
            "transaction_amount": "8000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
            "installments": 1,
            "order": {"id": "merchant_order_3"},
        }

        response = api_client.post(
            "/api/v1/payments/webhook/?data.id=99887769&type=payment",
            {"id": 12348, "type": "payment", "data": {"id": "99887769"}},
            format="json",
        )

        payment.refresh_from_db()
        order.refresh_from_db()

        assert response.status_code == 200
        assert payment.status == "approved"
        assert order.status == Order.Status.PAID

    @patch("apps.payments.views.MercadoPagoClient.get_payment")
    def test_feed_v2_payment_webhook_uses_id_and_topic_query_params(
        self,
        mock_get_payment,
        api_client,
        settings,
    ) -> None:
        """Mercado Pago Feed v2.0 payment callbacks should be treated as real payment webhooks."""
        settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
        settings.MERCADOPAGO_WEBHOOK_SECRET = ""
        settings.MERCADOPAGO_COLLECTOR_ID = "445566"
        order = OrderFactory(status="pending_payment", total=Decimal("8000.00"))
        OrderItemFactory(order=order)
        payment = PaymentFactory(order=order, amount=order.total, status="pending")
        mock_get_payment.return_value = {
            "id": 165395670924,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": str(order.id),
            "transaction_amount": "8000.00",
            "currency_id": "ARS",
            "collector_id": 445566,
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
            "installments": 1,
            "order": {"id": "merchant_order_feed_v2"},
        }

        response = api_client.post(
            "/api/v1/payments/webhook/?id=165395670924&topic=payment",
            {"id": 165395670924, "topic": "payment"},
            format="json",
        )

        payment.refresh_from_db()
        order.refresh_from_db()

        assert response.status_code == 200
        assert payment.status == Payment.Status.APPROVED
        assert payment.mp_payment_id == "165395670924"
        assert order.status == Order.Status.PREPARING

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
