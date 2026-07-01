"""Routes for the custom backoffice API."""

from __future__ import annotations

from django.urls import path

from .backoffice_views import (
    BackofficeCategoryDetailView,
    BackofficeCategoryListCreateView,
    BackofficeCustomerExportView,
    BackofficeCustomerListView,
    BackofficeDashboardView,
    BackofficeOrderActionView,
    BackofficeOrderDetailView,
    BackofficeOrderExportView,
    BackofficeOrderListView,
    BackofficePromoCodeDetailView,
    BackofficePromoCodeListCreateView,
    BackofficeSalesMetricsView,
    BackofficeVarietalDetailView,
    BackofficeVarietalListCreateView,
    BackofficeWineDetailView,
    BackofficeWineListCreateView,
)

app_name = "backoffice"

urlpatterns = [
    path("dashboard/", BackofficeDashboardView.as_view(), name="dashboard"),
    path("sales-metrics/", BackofficeSalesMetricsView.as_view(), name="sales-metrics"),
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
    path("orders/export.csv", BackofficeOrderExportView.as_view(), name="order-export"),
    path("orders/<uuid:pk>/", BackofficeOrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:pk>/action/", BackofficeOrderActionView.as_view(), name="order-action"),
    path("customers/", BackofficeCustomerListView.as_view(), name="customer-list"),
    path("customers/export.csv", BackofficeCustomerExportView.as_view(), name="customer-export"),
    path("promo-codes/", BackofficePromoCodeListCreateView.as_view(), name="promo-code-list"),
    path(
        "promo-codes/<int:pk>/",
        BackofficePromoCodeDetailView.as_view(),
        name="promo-code-detail",
    ),
]
