"""Shipping quote helpers for checkout."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone

from apps.catalog.models import Wine

from .models import Order


class ShippingQuoteError(Exception):
    """Raised when a checkout order cannot be quoted for shipping."""


@dataclass(frozen=True)
class ShippingQuote:
    """Normalized quote returned by the checkout shipping service."""

    shipping_method: str
    label: str
    description: str
    shipping_cost: Decimal
    provider: str
    service_level: str
    estimated_delivery: date | None


PROVINCE_ZONES: dict[str, str] = {
    "buenos aires": "metro",
    "caba": "metro",
    "ciudad autonoma de buenos aires": "metro",
    "cordoba": "centro",
    "santa fe": "centro",
    "entre rios": "centro",
    "la pampa": "centro",
    "san luis": "cuyo",
    "mendoza": "cuyo",
    "san juan": "cuyo",
    "catamarca": "noa",
    "jujuy": "noa",
    "la rioja": "noa",
    "salta": "noa",
    "santiago del estero": "noa",
    "tucuman": "noa",
    "chaco": "nea",
    "corrientes": "nea",
    "formosa": "nea",
    "misiones": "nea",
    "chubut": "patagonia",
    "neuquen": "patagonia",
    "rio negro": "patagonia",
    "santa cruz": "patagonia",
    "tierra del fuego": "patagonia",
}

ZONE_MULTIPLIERS: dict[str, Decimal] = {
    "metro": Decimal("1.00"),
    "centro": Decimal("1.08"),
    "cuyo": Decimal("0.96"),
    "noa": Decimal("1.20"),
    "nea": Decimal("1.24"),
    "patagonia": Decimal("1.34"),
}

STANDARD_BASE = Decimal("3200.00")
STANDARD_PER_BOTTLE = Decimal("480.00")
EXPRESS_BASE = Decimal("5200.00")
EXPRESS_PER_BOTTLE = Decimal("700.00")

STANDARD_ZONE_DAYS: dict[str, int] = {
    "metro": 4,
    "centro": 5,
    "cuyo": 4,
    "noa": 6,
    "nea": 6,
    "patagonia": 7,
}

EXPRESS_ZONE_DAYS: dict[str, int] = {
    "metro": 2,
    "centro": 3,
    "cuyo": 2,
    "noa": 4,
    "nea": 4,
    "patagonia": 5,
}


def _normalize_province(value: str) -> str:
    """Strip accents and spacing to compare provinces safely."""
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).strip().lower()


def _round_currency(amount: Decimal) -> Decimal:
    """Return a stable currency value rounded to the nearest peso."""
    return amount.quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)


def _resolve_zone(province: str) -> str:
    """Map a destination province into a coarse shipping zone."""
    return PROVINCE_ZONES.get(_normalize_province(province), "centro")


def _estimate_delivery(days: int) -> date:
    """Return a lightweight delivery estimate based on the current date."""
    return timezone.localdate() + timedelta(days=days)


class CheckoutShippingService:
    """Small backend-driven shipping quote engine for checkout."""

    provider_name = "andreani"

    def quote(
        self,
        *,
        wines: Iterable[Wine],
        quantities_by_wine_id: dict[object, int],
        shipping_address: dict[str, object],
    ) -> list[ShippingQuote]:
        """Return the available shipping methods for a checkout destination."""
        bottle_count = sum(quantities_by_wine_id.values())
        if bottle_count <= 0:
            raise ShippingQuoteError("Necesitamos al menos un producto para cotizar el envío.")

        zone = _resolve_zone(str(shipping_address.get("province") or ""))
        zone_multiplier = ZONE_MULTIPLIERS[zone]

        standard_amount = _round_currency(
            (STANDARD_BASE + STANDARD_PER_BOTTLE * max(bottle_count - 1, 0)) * zone_multiplier
        )
        express_amount = _round_currency(
            (EXPRESS_BASE + EXPRESS_PER_BOTTLE * max(bottle_count - 1, 0)) * zone_multiplier
        )

        return [
            ShippingQuote(
                shipping_method=Order.ShippingMethod.STANDARD,
                label=Order.ShippingMethod.STANDARD.label,
                description="Despacho nacional con Andreani, seguimiento y entrega estimada según zona.",
                shipping_cost=standard_amount,
                provider=self.provider_name,
                service_level="standard",
                estimated_delivery=_estimate_delivery(STANDARD_ZONE_DAYS[zone]),
            ),
            ShippingQuote(
                shipping_method=Order.ShippingMethod.EXPRESS,
                label=Order.ShippingMethod.EXPRESS.label,
                description=(
                    "Preparación prioritaria y despacho acelerado con Andreani "
                    "cuando la cobertura lo permite."
                ),
                shipping_cost=express_amount,
                provider=self.provider_name,
                service_level="express",
                estimated_delivery=_estimate_delivery(EXPRESS_ZONE_DAYS[zone]),
            ),
            ShippingQuote(
                shipping_method=Order.ShippingMethod.PICKUP,
                label=Order.ShippingMethod.PICKUP.label,
                description="Retiro coordinado en San Rafael, Mendoza.",
                shipping_cost=Decimal("0.00"),
                provider="pickup",
                service_level="pickup",
                estimated_delivery=None,
            ),
        ]

    def quote_for_method(
        self,
        *,
        wines: Iterable[Wine],
        quantities_by_wine_id: dict[object, int],
        shipping_address: dict[str, object],
        shipping_method: str,
    ) -> ShippingQuote:
        """Return the quote for the selected checkout method."""
        quotes = self.quote(
            wines=wines,
            quantities_by_wine_id=quantities_by_wine_id,
            shipping_address=shipping_address,
        )
        for quote in quotes:
            if quote.shipping_method == shipping_method:
                return quote
        raise ShippingQuoteError("No pudimos cotizar el método de envío seleccionado.")


def build_tracking_url(tracking_number: str) -> str | None:
    """Return the public Andreani tracking URL when a code is available."""
    normalized_tracking = tracking_number.strip()
    if not normalized_tracking:
        return None
    return settings.ANDREANI_TRACKING_URL_TEMPLATE.format(tracking_number=normalized_tracking)
