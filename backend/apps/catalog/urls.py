"""Catalog API routes."""

from __future__ import annotations

from django.urls import path

from .views import (
    CategoryListView,
    FeaturedWineListView,
    VarietalListView,
    WineDetailView,
    WineListView,
    WineReviewListCreateView,
)

app_name = "catalog"

urlpatterns = [
    path("wines/", WineListView.as_view(), name="wine-list"),
    path("wines/featured/", FeaturedWineListView.as_view(), name="wine-featured"),
    path("wines/<slug:slug>/", WineDetailView.as_view(), name="wine-detail"),
    path("wines/<slug:slug>/reviews/", WineReviewListCreateView.as_view(), name="wine-reviews"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("varietals/", VarietalListView.as_view(), name="varietal-list"),
]
