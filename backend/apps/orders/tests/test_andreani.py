"""Tests for Andreani shipment integration."""

from __future__ import annotations

import io
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib import error

import pytest
from django.core.cache import cache

from apps.automations.models import OutboxEvent
from apps.orders.andreani import AndreaniAPIError, AndreaniClient
from apps.orders.fulfillment import sync_andreani_shipping_order
from apps.orders.models import AndreaniShipment
from apps.orders.tests.factories import OrderFactory, OrderItemFactory


@pytest.mark.django_db
def test_andreani_payload_uses_order_data(settings) -> None:
    """The Andreani payload should map the order, addresses and recipient."""
    settings.ANDREANI_API_KEY = "token"
    settings.ANDREANI_CONTRACT = "CTR-1"
    settings.ANDREANI_CUSTOMER_BRANCH_ID = 15
    settings.ANDREANI_SENDER_DOCUMENT_NUMBER = "30712345678"
    settings.ANDREANI_SENDER_PHONE = "+5492604000000"
    settings.ANDREANI_SENDER_EMAIL = "logistica@laabeja.com"
    settings.ANDREANI_SENDER_NAME = "Bodega La Abeja"

    order = OrderFactory(
        customer_email="guest@example.com",
        subtotal=Decimal("9000.00"),
        total=Decimal("12000.00"),
    )
    OrderItemFactory(order=order, quantity=2, wine_name="Malbec Reserva", wine_sku="LAB-001")

    payload = AndreaniClient()._build_payload(order)

    assert payload["contrato"] == "CTR-1"
    assert payload["sucursalClienteID"] == 15
    assert payload["idPedido"] == order.order_number
    assert payload["destino"]["postal"]["codigoPostal"] == "5600"
    assert payload["destinatario"][0]["email"] == "guest@example.com"
    assert payload["bultos"][0]["descripcion"].startswith("2x Malbec Reserva")


@pytest.mark.django_db
@patch("apps.automations.outbox._dispatch_event")
def test_paid_order_queues_external_side_effects(mock_dispatch) -> None:
    """Paid orders should commit outbox work instead of calling providers inline."""
    order = OrderFactory(status="pending_payment", shipping_method="standard", tracking_number="")
    OrderItemFactory(order=order)

    order.status = "paid"
    order.save(update_fields=["status", "updated_at"])

    assert OutboxEvent.objects.filter(
        event_key=f"andreani-fulfillment:{order.id}",
        status=OutboxEvent.Status.PENDING,
    ).exists()
    assert OutboxEvent.objects.filter(event_type=OutboxEvent.EventType.ORDER_EMAIL).exists()


@pytest.mark.django_db
@patch("apps.automations.outbox._dispatch_event")
def test_pickup_order_skips_andreani(mock_dispatch) -> None:
    """Pickup orders should not create a carrier shipment."""
    order = OrderFactory(status="pending_payment", shipping_method="pickup", tracking_number="")
    OrderItemFactory(order=order)

    order.status = "paid"
    order.save(update_fields=["status", "updated_at"])

    assert not OutboxEvent.objects.filter(
        event_type=OutboxEvent.EventType.ANDREANI_FULFILLMENT
    ).exists()


def _successful_response(payload: bytes, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = payload
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


@patch("apps.orders.andreani.time.sleep")
@patch("apps.orders.andreani.request.urlopen")
def test_retries_5xx_then_returns_success(mock_urlopen, mock_sleep, settings) -> None:
    """Server failures are retried with bounded exponential backoff."""
    settings.ANDREANI_API_KEY = "token"
    settings.ANDREANI_MAX_ATTEMPTS = 3
    server_error = error.HTTPError(
        "https://apisqa.andreani.com/v1/localidades",
        503,
        "Unavailable",
        {},
        io.BytesIO(b'{"error":"temporary"}'),
    )
    mock_urlopen.side_effect = [
        server_error,
        _successful_response(b'[{"codigoPostal":"5600"}]'),
    ]

    result = AndreaniClient().get_localities(force_refresh=True)

    assert result == [{"codigoPostal": "5600"}]
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once()


@patch("apps.orders.andreani.time.sleep")
@patch("apps.orders.andreani.request.urlopen")
def test_does_not_retry_validation_400(mock_urlopen, mock_sleep, settings) -> None:
    """Validation failures must return immediately instead of duplicating requests."""
    settings.ANDREANI_API_KEY = "token"
    settings.ANDREANI_MAX_ATTEMPTS = 3
    mock_urlopen.side_effect = error.HTTPError(
        "https://apisqa.andreani.com/v2/ordenes-de-envio",
        400,
        "Bad Request",
        {},
        io.BytesIO(b'{"error":"invalid postal code"}'),
    )

    with pytest.raises(AndreaniAPIError) as raised:
        AndreaniClient()._request_json(
            method="POST",
            path="/v2/ordenes-de-envio",
            body={"idPedido": "LAB-1"},
            authenticated=True,
        )

    assert raised.value.status_code == 400
    assert raised.value.attempt_count == 1
    assert raised.value.retriable is False
    assert mock_urlopen.call_count == 1
    mock_sleep.assert_not_called()


@patch("apps.orders.andreani.request.urlopen")
def test_localities_are_cached(mock_urlopen, settings) -> None:
    """Master data should not hit Andreani again while its cache entry is alive."""
    settings.ANDREANI_API_KEY = "token"
    cache.clear()
    mock_urlopen.return_value = _successful_response(b'[{"codigoPostal":"5600"}]')
    client = AndreaniClient()

    first = client.get_localities()
    second = client.get_localities()

    assert first == second
    assert mock_urlopen.call_count == 1


@pytest.mark.django_db
@patch("apps.orders.fulfillment.AndreaniClient.download_label", return_value=b"%PDF-label")
@patch("apps.orders.fulfillment.AndreaniClient.create_shipping_order")
def test_label_is_copied_to_storage_and_duplicate_sync_is_skipped(
    mock_create_shipping_order,
    mock_download_label,
    settings,
    tmp_path,
) -> None:
    """A paid order gets one shipment record and a locally stored label."""
    settings.MEDIA_ROOT = tmp_path
    settings.ANDREANI_API_KEY = "token"
    mock_create_shipping_order.return_value = {
        "tracking_number": "360000000001",
        "estimated_delivery": None,
        "shipment_status": "Creada",
        "shipment_type": "B2C",
        "shipment_label": "https://apisqa.andreani.com/v2/labels/360000000001",
        "raw_response": {"estado": "Creada", "datoAuditable": "completo"},
    }
    order = OrderFactory(status="paid", shipping_method="standard", tracking_number="")
    OrderItemFactory(order=order)

    sync_andreani_shipping_order(order)
    sync_andreani_shipping_order(order)

    audit = AndreaniShipment.objects.get(order=order)
    assert audit.raw_response["datoAuditable"] == "completo"
    assert audit.label.name.endswith(".pdf")
    assert audit.label.read() == b"%PDF-label"
    assert mock_create_shipping_order.call_count == 1
    assert mock_download_label.call_count == 1
