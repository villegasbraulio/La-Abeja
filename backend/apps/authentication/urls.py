"""Authentication API routes."""

from __future__ import annotations

from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
    ProfileView,
    RefreshView,
    RegisterView,
)

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
