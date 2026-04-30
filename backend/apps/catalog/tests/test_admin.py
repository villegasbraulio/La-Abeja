"""Admin tests for catalog operations UX."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.authentication.tests.factories import UserFactory

from ..admin import WineAdminForm
from .factories import CategoryFactory, VarietalFactory, WineFactory


@pytest.fixture
def admin_client(db: object) -> Client:
    """Return a logged-in admin client."""
    user = UserFactory(is_staff=True, is_superuser=True)
    user.set_password("StrongPass123!")
    user.save(update_fields=["password"])
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_admin_index_renders_branded_dashboard(admin_client: Client) -> None:
    """The admin home should expose the friendlier internal dashboard copy."""
    response = admin_client.get(reverse("admin:index"))

    assert response.status_code == 200
    assert "Panel interno" in response.content.decode("utf-8")
    assert "Cargar nuevo vino" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_wine_admin_form_parses_human_inputs() -> None:
    """The admin form should convert multiline helpers into JSON fields."""
    category = CategoryFactory()
    varietal = VarietalFactory()

    form = WineAdminForm(
        data={
            "name": "Gran Malbec UX",
            "slug": "gran-malbec-ux",
            "category": category.pk,
            "varietal": varietal.pk,
            "vintage_year": 2023,
            "price": "6500.00",
            "compare_at_price": "7000.00",
            "cost_price": "3200.00",
            "stock": 14,
            "low_stock_threshold": 6,
            "sku": "LAB-UX-001",
            "alcohol_percentage": "14.1",
            "serving_temperature_min": 15,
            "serving_temperature_max": 18,
            "ageing_months": 8,
            "ageing_type": "oak",
            "tannins": 62,
            "acidity": 55,
            "body": 68,
            "sweetness": 18,
            "fruit_intensity": 72,
            "description": "Texto de venta.",
            "tasting_notes": "Notas de cata.",
            "winemaker_notes": "Notas del enologo.",
            "pairing_suggestions_text": "Asado\nQuesos duros",
            "blend_varietals_text": "Malbec: 85\nCabernet Franc: 15",
            "awards_text": "Decanter | 92 | 2024",
            "meta_title": "Meta title",
            "meta_description": "Meta description",
            "is_featured": True,
            "is_active": True,
            "is_limited_edition": False,
        }
    )

    assert form.is_valid(), form.errors

    wine = form.save()

    assert wine.pairing_suggestions == ["Asado", "Quesos duros"]
    assert wine.blend_varietals == [
        {"varietal": "Malbec", "percentage": 85},
        {"varietal": "Cabernet Franc", "percentage": 15},
    ]
    assert wine.awards == [{"award": "Decanter", "score": 92, "year": 2024}]
    assert wine.price == Decimal("6500.00")


@pytest.mark.django_db
def test_wine_changelist_is_accessible(admin_client: Client) -> None:
    """The wine changelist should be reachable for internal users."""
    WineFactory()

    response = admin_client.get(reverse("admin:catalog_wine_changelist"))

    assert response.status_code == 200
    assert "salud de stock" in response.content.decode("utf-8").lower()
