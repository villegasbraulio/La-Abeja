"""Catalog factories."""

from __future__ import annotations

from decimal import Decimal

import factory

from apps.authentication.tests.factories import UserFactory

from ..models import Category, Review, Varietal, Wine, WineImage


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory for categories."""

    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Tintos {n}")
    slug = factory.Sequence(lambda n: f"tintos-{n}")


class VarietalFactory(factory.django.DjangoModelFactory):
    """Factory for varietals."""

    class Meta:
        model = Varietal

    name = factory.Sequence(lambda n: f"Malbec {n}")
    slug = factory.Sequence(lambda n: f"malbec-{n}")


class WineFactory(factory.django.DjangoModelFactory):
    """Factory for wines."""

    class Meta:
        model = Wine

    category = factory.SubFactory(CategoryFactory)
    varietal = factory.SubFactory(VarietalFactory)
    name = factory.Sequence(lambda n: f"Gran Reserva {n}")
    slug = factory.Sequence(lambda n: f"gran-reserva-{n}")
    vintage_year = 2022
    price = Decimal("4500.00")
    compare_at_price = Decimal("5200.00")
    cost_price = Decimal("2200.00")
    stock = 20
    sku = factory.Sequence(lambda n: f"LAB-{n:05d}")
    alcohol_percentage = Decimal("14.2")
    serving_temperature_min = 16
    serving_temperature_max = 18
    ageing_months = 12
    ageing_type = Wine.AgeingType.OAK
    description = "Un vino elegante con gran profundidad."
    tasting_notes = "Frutas rojas maduras, especias y final largo."
    pairing_suggestions = ["Asado", "Quesos duros"]
    winemaker_notes = "Selección de parcelas viejas."
    awards = []
    is_featured = False
    is_active = True
    is_limited_edition = False


class WineImageFactory(factory.django.DjangoModelFactory):
    """Factory for wine images."""

    class Meta:
        model = WineImage

    wine = factory.SubFactory(WineFactory)
    url = "https://example.com/wine.jpg"
    alt_text = "Botella de vino"
    is_primary = True
    order = 0


class ReviewFactory(factory.django.DjangoModelFactory):
    """Factory for reviews."""

    class Meta:
        model = Review

    wine = factory.SubFactory(WineFactory)
    user = factory.SubFactory(UserFactory)
    order = None
    rating = 5
    title = "Excelente"
    body = "Gran vino para compartir."
    is_verified_purchase = False
    is_approved = True
