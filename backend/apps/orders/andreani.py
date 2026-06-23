"""Reliable Andreani API client for ecommerce shipping operations."""

from __future__ import annotations

import json
import time
from datetime import date
from decimal import Decimal
from typing import Any
from urllib import error, request
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache

from .models import Order
from .shipping import build_tracking_url

DEFAULT_BOTTLE_WEIGHT_KG = Decimal("1.25")
DEFAULT_PACKAGE_LENGTH_CM = 36
DEFAULT_PACKAGE_WIDTH_CM = 28
DEFAULT_PACKAGE_HEIGHT_CM = 18


class AndreaniAPIError(Exception):
    """Raised when an Andreani request cannot be completed safely."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: Any = None,
        attempt_count: int = 1,
        retriable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.attempt_count = attempt_count
        self.retriable = retriable


class AndreaniClient:
    """Andreani client with caching and a bounded retry policy."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or settings.ANDREANI_API_KEY).strip()
        self.base_url = settings.ANDREANI_API_BASE_URL.rstrip("/")
        self.max_attempts = max(int(settings.ANDREANI_MAX_ATTEMPTS), 1)
        self.retry_base_seconds = max(float(settings.ANDREANI_RETRY_BASE_SECONDS), 0)
        self.last_attempt_count = 0
        self.last_status_code: int | None = None

    def get_localities(self, *, force_refresh: bool = False) -> Any:
        """Return Andreani-normalized localities from cache when available."""
        return self._get_cached_master_data(
            path="/v1/localidades",
            cache_key="localities",
            force_refresh=force_refresh,
        )

    def get_branches(self, *, force_refresh: bool = False) -> Any:
        """Return Andreani branches from cache when available."""
        return self._get_cached_master_data(
            path="/v2/sucursales",
            cache_key="branches",
            force_refresh=force_refresh,
        )

    def create_shipping_order(
        self,
        order: Order,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an Andreani shipping order for a paid ecommerce order."""
        request_payload = payload or self._build_payload(order)
        response = self._request_json(
            method="POST",
            path=settings.ANDREANI_ORDER_PATH,
            body=request_payload,
            authenticated=True,
        )
        return self._normalize_response(response)

    def download_label(self, label_url: str) -> bytes:
        """Download a generated PDF/ZPL label from an approved Andreani host."""
        parsed_url = urlsplit(label_url)
        allowed_hosts = {host.lower() for host in settings.ANDREANI_LABEL_ALLOWED_HOSTS}
        if parsed_url.scheme != "https" or (parsed_url.hostname or "").lower() not in allowed_hosts:
            raise AndreaniAPIError("Andreani devolvió una URL de etiqueta no permitida.")
        return self._request_bytes(url=label_url, authenticated=True)

    def _get_cached_master_data(
        self,
        *,
        path: str,
        cache_key: str,
        force_refresh: bool,
    ) -> Any:
        namespaced_key = f"andreani:{self.base_url}:{cache_key}:v1"
        if not force_refresh:
            cached_value = cache.get(namespaced_key)
            if cached_value is not None:
                return cached_value

        response = self._request_json(
            method="GET",
            path=path,
            authenticated=False,
        )
        cache.set(namespaced_key, response, timeout=settings.ANDREANI_MASTER_DATA_CACHE_SECONDS)
        return response

    def _build_payload(self, order: Order) -> dict[str, Any]:
        """Map a local order into Andreani's shipping-order schema."""
        destination = order.shipping_address
        item_count = sum(item.quantity for item in order.items.all()) or 1
        total_weight = float(DEFAULT_BOTTLE_WEIGHT_KG * item_count)
        service_type = (
            settings.ANDREANI_SERVICE_TYPE_EXPRESS
            if order.shipping_method == Order.ShippingMethod.EXPRESS
            else settings.ANDREANI_SERVICE_TYPE_STANDARD
        )
        bulto_description = ", ".join(
            f"{item.quantity}x {item.wine_name}" for item in order.items.all()
        )

        payload = {
            "contrato": settings.ANDREANI_CONTRACT or None,
            "tipoDeServicio": service_type,
            "sucursalClienteID": settings.ANDREANI_CUSTOMER_BRANCH_ID,
            "origen": {
                "postal": {
                    "codigoPostal": settings.ANDREANI_ORIGIN_POSTAL_CODE,
                    "calle": settings.ANDREANI_ORIGIN_STREET,
                    "numero": settings.ANDREANI_ORIGIN_NUMBER,
                    "piso": settings.ANDREANI_ORIGIN_FLOOR,
                    "departamento": settings.ANDREANI_ORIGIN_APARTMENT,
                    "localidad": settings.ANDREANI_ORIGIN_CITY,
                    "region": settings.ANDREANI_ORIGIN_REGION,
                    "pais": settings.ANDREANI_ORIGIN_COUNTRY,
                }
            },
            "destino": {
                "postal": {
                    "codigoPostal": str(destination.get("postal_code") or ""),
                    "calle": str(destination.get("street") or ""),
                    "numero": str(destination.get("number") or ""),
                    "piso": str(destination.get("floor_apt") or ""),
                    "departamento": "",
                    "localidad": str(destination.get("city") or ""),
                    "region": str(destination.get("province") or ""),
                    "pais": str(destination.get("country") or "Argentina"),
                }
            },
            # This is stable and unique in our database and is also persisted as
            # AndreaniShipment.idempotency_key before the external call.
            "idPedido": order.order_number,
            "remitente": {
                "nombreCompleto": settings.ANDREANI_SENDER_NAME,
                "email": settings.ANDREANI_SENDER_EMAIL,
                "documentoTipo": settings.ANDREANI_SENDER_DOCUMENT_TYPE,
                "documentoNumero": settings.ANDREANI_SENDER_DOCUMENT_NUMBER,
                "telefonos": [{"tipo": 1, "numero": settings.ANDREANI_SENDER_PHONE}],
            },
            "destinatario": [
                {
                    "nombreCompleto": str(destination.get("recipient_name") or ""),
                    "email": order.customer_email,
                    "documentoTipo": "DNI",
                    "documentoNumero": "0",
                    "telefonos": [
                        {"tipo": 1, "numero": str(destination.get("phone") or "")}
                    ],
                }
            ],
            "remito": {
                "numeroRemito": order.order_number,
                "complementarios": [str(item.wine_sku) for item in order.items.all()],
            },
            "centroDeCostos": settings.ANDREANI_COST_CENTER or "ECOMMERCE",
            "productoAEntregar": bulto_description or "Pedido ecommerce",
            "tipoProducto": settings.ANDREANI_PRODUCT_TYPE or "VINOS",
            "categoriaFacturacion": settings.ANDREANI_BILLING_CATEGORY or "B2C",
            "pagoDestino": 0,
            "valorACobrar": 0,
            "bultos": [
                {
                    "kilos": total_weight,
                    "largoCm": DEFAULT_PACKAGE_LENGTH_CM,
                    "altoCm": DEFAULT_PACKAGE_HEIGHT_CM,
                    "anchoCm": DEFAULT_PACKAGE_WIDTH_CM,
                    "valorDeclaradoSinImpuestos": float(order.subtotal),
                    "valorDeclaradoConImpuestos": float(order.total),
                    "descripcion": bulto_description or "Pedido ecommerce",
                    "numeroDeEnvio": order.order_number,
                    "valorDeclarado": float(order.total),
                    "referencias": [{"meta": "order_id", "contenido": str(order.id)}],
                }
            ],
            "pagoPendienteEnMostrador": False,
        }
        return _remove_empty_values(payload)

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        authenticated: bool,
        body: dict[str, Any] | None = None,
    ) -> Any:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        content, status_code = self._execute_request(
            method=method,
            url=f"{self.base_url}{path}",
            data=payload,
            authenticated=authenticated,
            accept="application/json",
        )
        self.last_status_code = status_code
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AndreaniAPIError(
                "Andreani devolvió una respuesta inválida.",
                status_code=status_code,
                response_body=content.decode("utf-8", errors="replace"),
                attempt_count=self.last_attempt_count,
            ) from exc

    def _request_bytes(self, *, url: str, authenticated: bool) -> bytes:
        content, status_code = self._execute_request(
            method="GET",
            url=url,
            data=None,
            authenticated=authenticated,
            accept="application/pdf, application/zpl, application/octet-stream",
        )
        self.last_status_code = status_code
        return content

    def _execute_request(
        self,
        *,
        method: str,
        url: str,
        data: bytes | None,
        authenticated: bool,
        accept: str,
    ) -> tuple[bytes, int]:
        headers = {"Accept": accept}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if authenticated:
            headers.update(self._authentication_headers())

        for attempt in range(1, self.max_attempts + 1):
            self.last_attempt_count = attempt
            http_request = request.Request(
                url=url,
                data=data,
                method=method,
                headers=headers,
            )
            try:
                with request.urlopen(
                    http_request,
                    timeout=settings.ANDREANI_REQUEST_TIMEOUT_SECONDS,
                ) as response:
                    return response.read(), int(response.status)
            except error.HTTPError as exc:
                response_bytes = exc.read()
                response_body = _decode_response_body(response_bytes)
                retriable = exc.code >= 500
                if retriable and attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise AndreaniAPIError(
                    f"Andreani devolvió HTTP {exc.code}: {response_body or exc.reason}",
                    status_code=exc.code,
                    response_body=response_body,
                    attempt_count=attempt,
                    retriable=retriable,
                ) from exc
            except (error.URLError, TimeoutError) as exc:
                if attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise AndreaniAPIError(
                    "No pudimos comunicarnos con Andreani.",
                    attempt_count=attempt,
                    retriable=True,
                ) from exc

        raise AssertionError("Unreachable Andreani retry state")

    def _sleep_before_retry(self, completed_attempt: int) -> None:
        time.sleep(self.retry_base_seconds * (2 ** (completed_attempt - 1)))

    def _authentication_headers(self) -> dict[str, str]:
        token = self.api_key.removeprefix("Bearer ").removeprefix("bearer ").strip()
        if not token:
            raise AndreaniAPIError("Andreani no está configurado en este entorno.")
        return {
            "Authorization": f"Bearer {token}",
            "x-authorization-token": token,
        }

    def _normalize_response(self, response: Any) -> dict[str, Any]:
        """Return local fields while preserving the complete raw response."""
        if not isinstance(response, dict):
            raise AndreaniAPIError(
                "Andreani devolvió una respuesta inesperada.",
                status_code=self.last_status_code,
                response_body=response,
                attempt_count=self.last_attempt_count,
            )
        bultos = response.get("bultos") if isinstance(response.get("bultos"), list) else []
        envios = response.get("envios") if isinstance(response.get("envios"), list) else []
        first_package = next(
            (item for item in [*bultos, *envios] if isinstance(item, dict)),
            {},
        )
        tracking_number = str(
            first_package.get("numeroDeEnvio")
            or first_package.get("numeroEnvio")
            or response.get("agrupadorDeBultos")
            or ""
        ).strip()
        estimated_delivery_raw = str(response.get("fechaEstimadaDeEntrega") or "").strip()

        return {
            "tracking_number": tracking_number,
            "tracking_url": build_tracking_url(tracking_number),
            "estimated_delivery": _parse_date_prefix(estimated_delivery_raw),
            "shipment_status": str(response.get("estado") or ""),
            "shipment_type": str(response.get("tipo") or ""),
            "shipment_label": _find_label_url(response, first_package),
            "raw_response": response,
        }


def _find_label_url(response: dict[str, Any], first_package: dict[str, Any]) -> str:
    direct_candidates = (
        response.get("etiquetaRemito"),
        response.get("etiquetaAgrupador"),
        first_package.get("etiqueta"),
    )
    for candidate in direct_candidates:
        if isinstance(candidate, str) and candidate.startswith("https://"):
            return candidate

    linking = first_package.get("linking")
    if isinstance(linking, list):
        for link in linking:
            if not isinstance(link, dict):
                continue
            candidate = link.get("contenido")
            if str(link.get("meta") or "").lower() == "etiqueta" and isinstance(candidate, str):
                return candidate
    return ""


def _decode_response_body(value: bytes) -> Any:
    decoded = value.decode("utf-8", errors="replace")
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return decoded


def _parse_date_prefix(value: str) -> date | None:
    """Parse an ISO-like datetime/date string into a date when possible."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _remove_empty_values(value: Any) -> Any:
    """Recursively remove empty values from a nested payload."""
    if isinstance(value, dict):
        cleaned = {
            key: _remove_empty_values(item)
            for key, item in value.items()
            if item not in (None, "", [], {})
        }
        return {key: item for key, item in cleaned.items() if item not in (None, "", [], {})}
    if isinstance(value, list):
        cleaned_list = [_remove_empty_values(item) for item in value]
        return [item for item in cleaned_list if item not in (None, "", [], {})]
    return value
