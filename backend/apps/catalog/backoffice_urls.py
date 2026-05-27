"""Routes for the custom backoffice API."""

from __future__ import annotations

from django.urls import path

from .backoffice_views import (
    BackofficeCategoryDetailView,
    BackofficeCategoryListCreateView,
    BackofficeDashboardView,
    BackofficeOrderDetailView,
    BackofficeOrderListView,
    BackofficeVarietalDetailView,
    BackofficeVarietalListCreateView,
    BackofficeWineDetailView,
    BackofficeWineListCreateView,
)

app_name = "backoffice"

urlpatterns = [
    path("dashboard/", BackofficeDashboardView.as_view(), name="dashboard"),
    path("categories/", BackofficeCategoryListCreateView.as_view(), name="category-list"),
    path(
        "categories/<int:pk>/",
        BackofficeCategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("varietals/", BackofficeVarietalListCreateView.as_view(), name="varietal-list"),
    path(
        "varietals/<int:pk>/",
        BackofficeVarietalDetailView.as_view(),
        name="varietal-detail",
    ),
    path("wines/", BackofficeWineListCreateView.as_view(), name="wine-list"),
    path("wines/<uuid:pk>/", BackofficeWineDetailView.as_view(), name="wine-detail"),
    path("orders/", BackofficeOrderListView.as_view(), name="order-list"),
    path("orders/<uuid:pk>/", BackofficeOrderDetailView.as_view(), name="order-detail"),
]
