"""Order API routes."""

from __future__ import annotations

from django.urls import path

from .views import OrderCancelView, OrderDetailView, OrderListCreateView

app_name = "orders"

urlpatterns = [
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
