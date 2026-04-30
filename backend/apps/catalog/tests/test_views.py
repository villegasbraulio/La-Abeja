"""Catalog API tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from .factories import (
    CategoryFactory,
    ReviewFactory,
    VarietalFactory,
    WineFactory,
    WineImageFactory,
)


@pytest.mark.django_db
class TestWineListView:
    """Catalog list endpoint coverage."""

    def test_returns_only_active_wines(self, api_client, wine_factory) -> None:
        wine_factory.create_batch(3, is_active=True)
        wine_factory.create_batch(2, is_active=False)

        response = api_client.get("/api/v1/catalog/wines/")

        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_filter_by_category_slug(self, api_client, wine_factory) -> None:
        category = CategoryFactory(slug="tintos")
        wine_factory.create_batch(3, category=category, is_active=True)
        wine_factory.create_batch(2, is_active=True)

        response = api_client.get("/api/v1/catalog/wines/?category=tintos")

        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_filter_by_price_range(self, api_client, wine_factory) -> None:
        wine_factory.create(price=Decimal("1500.00"), is_active=True)
        wine_factory.create(price=Decimal("3000.00"), is_active=True)
        wine_factory.create(price=Decimal("5000.00"), is_active=True)

        response = api_client.get("/api/v1/catalog/wines/?min_price=2000&max_price=4000")

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_search_by_name(self, api_client, wine_factory) -> None:
        wine_factory.create(name="Gran Malbec Reserva", slug="gran-malbec-reserva", is_active=True)
        wine_factory.create(
            name="Chardonnay Clásico",
            slug="chardonnay-clasico",
            varietal=VarietalFactory(name="Chardonnay", slug="chardonnay"),
            is_active=True,
        )

        response = api_client.get("/api/v1/catalog/wines/?search=malbec")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert "Malbec" in response.data["results"][0]["name"]

    def test_returns_primary_image(self, api_client) -> None:
        wine = WineFactory(is_active=True)
        WineImageFactory(wine=wine, is_primary=True, url="https://example.com/primary.jpg")

        response = api_client.get("/api/v1/catalog/wines/")

        assert response.status_code == 200
        assert response.data["results"][0]["primary_image"] == "https://example.com/primary.jpg"

    def test_featured_endpoint_returns_unpaginated_featured_wines(self, api_client) -> None:
        featured = WineFactory(is_active=True, is_featured=True)
        WineFactory(is_active=True, is_featured=False)

        response = api_client.get("/api/v1/catalog/wines/featured/")

        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(featured.id)


@pytest.mark.django_db
def test_wine_detail_returns_recent_reviews(api_client) -> None:
    """Wine detail should include recent approved reviews."""
    wine = WineFactory(slug="malbec-reserva")
    ReviewFactory.create_batch(2, wine=wine, is_approved=True)

    response = api_client.get("/api/v1/catalog/wines/malbec-reserva/")

    assert response.status_code == 200
    assert len(response.data["recent_reviews"]) == 2


@pytest.mark.django_db
def test_create_review_requires_authentication(api_client, wine_factory) -> None:
    """Anonymous users cannot create reviews."""
    wine = wine_factory()
    response = api_client.post(
        f"/api/v1/catalog/wines/{wine.slug}/reviews/",
        {"rating": 5, "title": "Excelente", "body": "Muy buen vino"},
        format="json",
    )

    assert response.status_code == 401
