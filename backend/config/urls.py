"""Project URL configuration."""

from __future__ import annotations

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthcheck(_: object) -> JsonResponse:
    """Return a simple application health response."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/backoffice/", include("apps.catalog.backoffice_urls")),
    path("api/v1/backoffice/", include("apps.reservations.backoffice_urls")),
]
