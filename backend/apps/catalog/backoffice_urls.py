"""Routes for the custom backoffice API."""

from __future__ import annotations

from django.urls import path

from .backoffice_views import (
    BackofficeCategoryDetailView,
    BackofficeCategoryListCreateView,
    BackofficeDashboardView,
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
]
