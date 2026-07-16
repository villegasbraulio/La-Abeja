"""Unit tests for the Mercado Pago SDK wrapper."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from apps.orders.tests.factories import OrderFactory, OrderItemFactory
from apps.payments.mercadopago import MercadoPagoAPIError, MercadoPagoClient


class FakePreferenceResource:
    """Minimal fake preference resource for SDK tests."""

    def __init__(self, response):
        self.response = response

    def create(self, payload, request_options=None):
        self.payload = payload
        self.request_options = request_options
        return self.response


class FakePaymentResource:
    """Minimal fake payment resource for SDK tests."""

    def __init__(self, response):
        self.response = response

    def get(self, payment_id, request_options=None):
        self.payment_id = payment_id
        self.request_options = request_options
        return self.response

    def search(self, filters=None, request_options=None):
        self.filters = filters
        self.request_options = request_options
        return {"status": 200, "response": {"results": [self.response["response"]]}}


class FakeSDK:
    """Small test double for the official SDK."""

    def __init__(self, access_token, http_client=None, request_options=None):
        self.access_token = access_token
        self.http_client = http_client
        self.request_options = request_options
        self.preference_resource = FakePreferenceResource(
            {
                "status": 201,
                "response": {
                    "id": "pref_123",
                    "init_point": "https://example.com/init",
                },
            }
        )
        self.payment_resource = FakePaymentResource(
            {
                "status": 200,
                "response": {
                    "id": 998877,
                    "status": "approved",
                },
            }
        )

    def preference(self):
        return self.preference_resource

    def payment(self):
        return self.payment_resource


@pytest.mark.django_db
def test_client_uses_official_sdk_for_preferences(monkeypatch, settings) -> None:
    """Preference creation should delegate to the official Mercado Pago SDK."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
    settings.FRONTEND_URL = "https://tienda.example.com"
    settings.BACKEND_URL = "https://api.example.com"
    fake_module = type("FakeMercadoPagoModule", (), {"SDK": FakeSDK})
    monkeypatch.setattr("apps.payments.mercadopago.mercadopago", fake_module)

    order = OrderFactory(total=Decimal("9500.00"), shipping_cost=Decimal("500.00"))
    OrderItemFactory(
        order=order,
        wine_name="Malbec Reserva",
        wine_sku="LAB-MAL-001",
        quantity=2,
        unit_price=Decimal("4500.00"),
        subtotal=Decimal("9000.00"),
    )

    client = MercadoPagoClient()
    response = client.create_preference(order)

    assert response["id"] == "pref_123"
    assert client.sdk.access_token == "test-token"
    assert client.sdk.preference_resource.payload["external_reference"] == str(order.id)
    assert len(client.sdk.preference_resource.payload["items"]) == 2
    assert client.sdk.preference_resource.payload["items"][0] == {
        "id": "LAB-MAL-001",
        "title": "Malbec Reserva",
        "description": "SKU LAB-MAL-001 · 2 botella(s)",
        "currency_id": "ARS",
        "quantity": 2,
        "unit_price": 4500.0,
    }
    assert client.sdk.preference_resource.payload["items"][-1]["unit_price"] == 500.0
    assert client.sdk.preference_resource.payload["items"][-1]["title"].startswith("Envío - ")
    assert (
        client.sdk.preference_resource.payload["items"][-1]["description"]
        == "San Rafael, Mendoza"
    )
    assert (
        client.sdk.preference_resource.payload["notification_url"]
        == "https://api.example.com/api/v1/payments/webhook/"
    )
    assert client.sdk.preference_resource.payload["back_urls"]["success"].startswith(
        "https://tienda.example.com/checkout/resultado"
    )
    assert "shipments" not in client.sdk.preference_resource.payload
    assert client.sdk.preference_resource.request_options.custom_headers == {
        "x-idempotency-key": f"mercadopago:preference:{order.id}"
    }


@pytest.mark.django_db
def test_client_skips_back_urls_on_local_frontend(monkeypatch, settings) -> None:
    """Local frontend URLs should not send invalid back_urls to Mercado Pago."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
    settings.FRONTEND_URL = "http://127.0.0.1:3000"
    settings.BACKEND_URL = "http://127.0.0.1:8000"
    fake_module = type("FakeMercadoPagoModule", (), {"SDK": FakeSDK})
    monkeypatch.setattr("apps.payments.mercadopago.mercadopago", fake_module)

    order = OrderFactory(total=Decimal("9800.00"), shipping_cost=Decimal("500.00"))
    OrderItemFactory(order=order)

    client = MercadoPagoClient()
    client.create_preference(order)

    assert "back_urls" not in client.sdk.preference_resource.payload
    assert "auto_return" not in client.sdk.preference_resource.payload
    assert "notification_url" not in client.sdk.preference_resource.payload


@pytest.mark.django_db
def test_client_skips_invalid_public_urls(monkeypatch, settings) -> None:
    """Malformed environment URLs should not break preference creation."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
    settings.FRONTEND_URL = "la-abeja.vercel.app"
    settings.BACKEND_URL = "la-abeja-backend.onrender.com"
    fake_module = type("FakeMercadoPagoModule", (), {"SDK": FakeSDK})
    monkeypatch.setattr("apps.payments.mercadopago.mercadopago", fake_module)

    order = OrderFactory(total=Decimal("9800.00"), shipping_cost=Decimal("500.00"))
    OrderItemFactory(order=order)

    client = MercadoPagoClient()
    response = client.create_preference(order)

    assert response["id"] == "pref_123"
    assert "notification_url" not in client.sdk.preference_resource.payload
    assert "back_urls" not in client.sdk.preference_resource.payload
    assert "auto_return" not in client.sdk.preference_resource.payload


@pytest.mark.django_db
def test_client_includes_guest_access_token_in_back_urls(monkeypatch, settings) -> None:
    """Guest checkout returns should preserve the signed order access token."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"
    settings.FRONTEND_URL = "https://tienda.example.com"
    settings.BACKEND_URL = "https://api.example.com"
    fake_module = type("FakeMercadoPagoModule", (), {"SDK": FakeSDK})
    monkeypatch.setattr("apps.payments.mercadopago.mercadopago", fake_module)

    order = OrderFactory(
        user=None,
        customer_email="guest@example.com",
        total=Decimal("9800.00"),
        shipping_cost=Decimal("500.00"),
    )
    OrderItemFactory(order=order)

    client = MercadoPagoClient()
    client.create_preference(order)

    success_url = client.sdk.preference_resource.payload["back_urls"]["success"]
    parsed = urlsplit(success_url)
    params = parse_qs(parsed.query)

    assert params["order_id"] == [str(order.id)]
    assert params["status"] == ["approved"]
    assert "guest_access_token" in params


def test_client_raises_readable_errors_from_sdk(monkeypatch, settings) -> None:
    """SDK errors should be surfaced with a clear message."""
    settings.MERCADOPAGO_ACCESS_TOKEN = "test-token"

    class ErrorSDK(FakeSDK):
        def __init__(self, access_token, http_client=None, request_options=None):
            super().__init__(access_token, http_client=http_client, request_options=request_options)
            self.payment_resource = FakePaymentResource(
                {
                    "status": 404,
                    "response": {
                        "message": "payment not found",
                    },
                }
            )

    fake_module = type("FakeMercadoPagoModule", (), {"SDK": ErrorSDK})
    monkeypatch.setattr("apps.payments.mercadopago.mercadopago", fake_module)

    client = MercadoPagoClient()

    with pytest.raises(MercadoPagoAPIError, match="payment not found"):
        client.get_payment("missing-payment")
