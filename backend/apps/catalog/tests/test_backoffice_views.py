"""Integration tests for custom backoffice catalog endpoints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.tests.factories import UserFactory
from apps.orders.tests.factories import OrderFactory, OrderItemFactory
from apps.payments.tests.factories import PaymentFactory

from .factories import CategoryFactory, VarietalFactory, WineFactory, WineImageFactory


@pytest.fixture
def staff_client() -> tuple[APIClient, object]:
    """Return a JWT-authenticated staff client."""
    user = UserFactory(is_staff=True, is_superuser=True)
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, user


@pytest.mark.django_db
def test_backoffice_dashboard_requires_staff(
    authenticated_client: tuple[APIClient, object],
) -> None:
    """Regular authenticated users should be blocked from the backoffice."""
    client, _ = authenticated_client

    response = client.get("/api/v1/backoffice/dashboard/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_backoffice_dashboard_returns_summary(staff_client: tuple[APIClient, object]) -> None:
    """Staff should receive dashboard KPIs."""
    client, _ = staff_client
    wine = WineFactory(stock=3, low_stock_threshold=5, is_active=True)
    WineImageFactory(wine=wine, is_primary=True)

    response = client.get("/api/v1/backoffice/dashboard/")

    assert response.status_code == 200
    assert response.data["total_wines"] >= 1
    assert response.data["low_stock_wines"] >= 1
    assert response.data["low_stock_items"][0]["name"] == wine.name


@pytest.mark.django_db
def test_backoffice_sales_metrics_returns_commercial_dashboard(
    staff_client: tuple[APIClient, object],
) -> None:
    """Staff should receive sales KPIs and grouped commercial indicators."""
    client, _ = staff_client
    order = OrderFactory(status="delivered")
    OrderItemFactory(order=order, quantity=3)
    PaymentFactory(order=order, status="approved")

    response = client.get("/api/v1/backoffice/sales-metrics/?period=last_30_days")

    assert response.status_code == 200
    assert response.data["summary"]["order_count"] == 1
    assert response.data["summary"]["bottles_sold"] == 3
    assert response.data["by_product"]["results"]
    assert response.data["timeline"]["results"]


@pytest.mark.django_db
def test_staff_can_create_category(staff_client: tuple[APIClient, object]) -> None:
    """Staff can create categories through the backoffice API."""
    client, _ = staff_client

    response = client.post(
        "/api/v1/backoffice/categories/",
        {
            "name": "Espumantes",
            "description": "Metodo tradicional.",
            "icon": "sparkles",
            "order": 2,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["slug"] == "espumantes"


@pytest.mark.django_db
def test_staff_can_update_and_delete_category(staff_client: tuple[APIClient, object]) -> None:
    """Staff can update and delete categories."""
    client, _ = staff_client
    category = CategoryFactory(name="Tintos", slug="tintos")

    patch_response = client.patch(
        f"/api/v1/backoffice/categories/{category.id}/",
        {"name": "Tintos Reserva", "slug": ""},
        format="json",
    )
    delete_response = client.delete(f"/api/v1/backoffice/categories/{category.id}/")

    assert patch_response.status_code == 200
    assert patch_response.data["slug"] == "tintos-reserva"
    assert delete_response.status_code == 204


@pytest.mark.django_db
def test_staff_can_create_and_update_varietal(staff_client: tuple[APIClient, object]) -> None:
    """Staff can create and update varietals."""
    client, _ = staff_client

    create_response = client.post(
        "/api/v1/backoffice/varietals/",
        {
            "name": "Bonarda",
            "description": "Fruta roja vibrante.",
            "origin_region": "San Rafael",
        },
        format="json",
    )

    varietal_id = create_response.data["id"]
    update_response = client.patch(
        f"/api/v1/backoffice/varietals/{varietal_id}/",
        {"origin_region": "Mendoza"},
        format="json",
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert update_response.data["origin_region"] == "Mendoza"


@pytest.mark.django_db
def test_staff_can_list_wines(staff_client: tuple[APIClient, object]) -> None:
    """Staff can load the wine manager list."""
    client, _ = staff_client
    wine = WineFactory(is_active=True, is_featured=True)
    WineImageFactory(wine=wine, is_primary=True, url="https://example.com/hero.jpg")

    response = client.get("/api/v1/backoffice/wines/")

    assert response.status_code == 200
    assert response.data["results"][0]["name"] == wine.name
    assert response.data["results"][0]["primary_image"] == "https://example.com/hero.jpg"


@pytest.mark.django_db
def test_staff_can_create_wine_with_images(staff_client: tuple[APIClient, object]) -> None:
    """Staff can create wines with images through the custom backoffice."""
    client, _ = staff_client
    category = CategoryFactory()
    varietal = VarietalFactory()

    response = client.post(
        "/api/v1/backoffice/wines/",
        {
            "name": "Gran Blend de Operaciones",
            "category": category.id,
            "varietal": varietal.id,
            "vintage_year": 2024,
            "price": "7800.00",
            "compare_at_price": "8600.00",
            "cost_price": "3500.00",
            "stock": 18,
            "low_stock_threshold": 6,
            "sku": "LAB-OPS-001",
            "alcohol_percentage": "14.0",
            "serving_temperature_min": 15,
            "serving_temperature_max": 18,
            "ageing_months": 10,
            "ageing_type": "oak",
            "tannins": 60,
            "acidity": 50,
            "body": 72,
            "sweetness": 18,
            "fruit_intensity": 78,
            "description": "Texto comercial.",
            "tasting_notes": "Notas intensas.",
            "pairing_suggestions": ["Asado", "Quesos"],
            "winemaker_notes": "Lote especial.",
            "awards": [{"award": "Decanter", "score": 92, "year": 2024}],
            "blend_varietals": [{"varietal": "Malbec", "percentage": 80}],
            "meta_title": "Gran Blend",
            "meta_description": "Detalle del vino.",
            "is_featured": True,
            "is_active": True,
            "is_limited_edition": False,
            "images": [
                {
                    "url": "https://example.com/gran-blend.jpg",
                    "alt_text": "Botella principal",
                    "is_primary": True,
                    "order": 0,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["slug"] == "gran-blend-de-operaciones"
    assert len(response.data["images"]) == 1


@pytest.mark.django_db
def test_staff_can_update_and_delete_wine(staff_client: tuple[APIClient, object]) -> None:
    """Staff can update a wine and replace its images."""
    client, _ = staff_client
    wine = WineFactory()

    patch_response = client.patch(
        f"/api/v1/backoffice/wines/{wine.id}/",
        {
            "price": "9999.00",
            "stock": 4,
            "images": [
                {
                    "url": "https://example.com/new-primary.jpg",
                    "alt_text": "Nueva principal",
                    "is_primary": True,
                    "order": 0,
                }
            ],
        },
        format="json",
    )
    delete_response = client.delete(f"/api/v1/backoffice/wines/{wine.id}/")

    assert patch_response.status_code == 200
    assert patch_response.data["price"] == "9999.00"
    assert patch_response.data["images"][0]["url"] == "https://example.com/new-primary.jpg"
    assert delete_response.status_code == 204


@pytest.mark.django_db
def test_staff_can_list_orders(staff_client: tuple[APIClient, object]) -> None:
    """Staff can inspect the internal order queue."""
    client, _ = staff_client
    order = OrderFactory()
    OrderItemFactory(order=order, quantity=2)
    PaymentFactory(order=order)

    response = client.get("/api/v1/backoffice/orders/")

    assert response.status_code == 200
    assert response.data["results"][0]["order_number"] == order.order_number
    assert response.data["results"][0]["item_count"] == 2


@pytest.mark.django_db
def test_staff_can_retrieve_order_detail(staff_client: tuple[APIClient, object]) -> None:
    """Staff can open the detail view for a specific order."""
    client, _ = staff_client
    order = OrderFactory()
    OrderItemFactory(order=order)
    PaymentFactory(order=order)

    response = client.get(f"/api/v1/backoffice/orders/{order.id}/")

    assert response.status_code == 200
    assert response.data["order_number"] == order.order_number
    assert response.data["customer_email"] == order.user.email
    assert response.data["payment"]["mp_preference_id"].startswith("pref_")


@pytest.mark.django_db
def test_staff_can_list_guest_orders_without_crashing(staff_client: tuple[APIClient, object]) -> None:
    """Guest orders should render in backoffice using checkout contact fallbacks."""
    client, _ = staff_client
    order = OrderFactory(
        user=None,
        customer_email="guest@example.com",
        shipping_address={
            "recipient_name": "Maria Guest",
            "street": "Av. San Martin",
            "number": "450",
            "floor_apt": "",
            "city": "San Rafael",
            "province": "Mendoza",
            "postal_code": "5600",
            "country": "Argentina",
            "phone": "+5492604555555",
        },
    )
    OrderItemFactory(order=order, quantity=1)

    response = client.get("/api/v1/backoffice/orders/")

    assert response.status_code == 200
    assert response.data["results"][0]["id"] == str(order.id)
    assert response.data["results"][0]["customer_name"] == "Maria Guest"
    assert response.data["results"][0]["customer_email"] == "guest@example.com"
    assert response.data["results"][0]["customer_phone"] == "+5492604555555"


@pytest.mark.django_db
def test_staff_can_update_order_operation_fields(staff_client: tuple[APIClient, object]) -> None:
    """Staff can move an order and add tracking from the custom backoffice."""
    client, _ = staff_client
    order = OrderFactory(status="pending_payment")
    OrderItemFactory(order=order)

    response = client.patch(
        f"/api/v1/backoffice/orders/{order.id}/action/",
        {
            "status": "preparing",
            "tracking_number": "AND-123",
            "estimated_delivery": "2026-07-05",
            "notes": "Sale en la próxima tanda.",
        },
        format="json",
    )

    order.refresh_from_db()
    assert response.status_code == 200
    assert order.status == "preparing"
    assert order.tracking_number == "AND-123"
    assert response.data["notes"] == "Sale en la próxima tanda."


@pytest.mark.django_db
def test_staff_can_list_customers_and_export_csv(staff_client: tuple[APIClient, object]) -> None:
    """Customer rows and CSV export should be available to staff."""
    client, _ = staff_client
    user = UserFactory(email="compradora@example.com", is_staff=False)
    order = OrderFactory(user=user, customer_email=user.email, status="delivered")
    OrderItemFactory(order=order)

    list_response = client.get("/api/v1/backoffice/customers/")
    export_response = client.get("/api/v1/backoffice/customers/export.csv")

    assert list_response.status_code == 200
    assert list_response.data["results"][0]["email"] == "compradora@example.com"
    assert list_response.data["results"][0]["orders_count"] == 1
    assert export_response.status_code == 200
    assert b"compradora@example.com" in export_response.content


@pytest.mark.django_db
def test_staff_can_create_and_pause_promo_code(staff_client: tuple[APIClient, object]) -> None:
    """Staff can manage simple promo codes."""
    client, _ = staff_client
    now = timezone.now()

    create_response = client.post(
        "/api/v1/backoffice/promo-codes/",
        {
            "code": "ABEJA10",
            "discount_type": "percentage",
            "discount_value": "10.00",
            "min_order_amount": "0.00",
            "max_uses": 20,
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=30)).isoformat(),
            "is_active": True,
        },
        format="json",
    )
    promo_id = create_response.data["id"]
    patch_response = client.patch(
        f"/api/v1/backoffice/promo-codes/{promo_id}/",
        {"is_active": False},
        format="json",
    )

    assert create_response.status_code == 201
    assert patch_response.status_code == 200
    assert patch_response.data["is_active"] is False
