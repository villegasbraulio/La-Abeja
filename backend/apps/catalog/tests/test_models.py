"""Catalog model tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from .factories import WineFactory


@pytest.mark.django_db
def test_wine_str_returns_name() -> None:
    """Wine string representation should use the product name."""
    wine = WineFactory(name="Malbec Reserva")
    assert str(wine) == "Malbec Reserva"


@pytest.mark.django_db
def test_wine_compare_price_can_be_blank() -> None:
    """Compare-at price should be optional."""
    wine = WineFactory(compare_at_price=None, price=Decimal("3000.00"))
    assert wine.compare_at_price is None
