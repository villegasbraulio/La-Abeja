"""Payment API routes."""

from __future__ import annotations

from django.urls import path

from .views import CreatePreferenceView, PaymentWebhookView

app_name = "payments"

urlpatterns = [
    path("create-preference/", CreatePreferenceView.as_view(), name="create-preference"),
    path("webhook/", PaymentWebhookView.as_view(), name="webhook"),
]
