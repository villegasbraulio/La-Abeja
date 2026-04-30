"""Authentication API tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.authentication.tests.factories import UserFactory


@pytest.mark.django_db
def test_register_user() -> None:
    """Users can register with valid data."""
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "buyer@example.com",
            "first_name": "Ana",
            "last_name": "Luna",
            "password": "StrongPass123!",
        },
        format="json",
    )
    assert response.status_code == 201
    assert "access" in response.data
    assert response.data["user"]["email"] == "buyer@example.com"


@pytest.mark.django_db
def test_login_user() -> None:
    """Users can obtain JWT tokens with email and password."""
    user = UserFactory(email="buyer@example.com")
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert response.data["user"]["email"] == user.email


@pytest.mark.django_db
def test_profile_requires_authentication() -> None:
    """Anonymous profile requests should be rejected."""
    client = APIClient()
    response = client.get("/api/v1/auth/profile/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_profile_returns_current_user(authenticated_client: tuple[APIClient, object]) -> None:
    """Authenticated users can fetch their profile."""
    client, user = authenticated_client
    response = client.get("/api/v1/auth/profile/")
    assert response.status_code == 200
    assert response.data["email"] == user.email


@pytest.mark.django_db
@patch("apps.authentication.views.EmailService.send_transactional")
def test_password_reset_sends_email(mock_send: object) -> None:
    """Password reset requests should trigger transactional email."""
    user = UserFactory(email="reset@example.com", first_name="Lucia")
    client = APIClient()
    response = client.post("/api/v1/auth/password/reset/", {"email": user.email}, format="json")
    assert response.status_code == 200
    mock_send.assert_called_once()


@pytest.mark.django_db
def test_password_reset_confirm_updates_password() -> None:
    """Valid reset tokens should allow setting a new password."""
    user = UserFactory()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    client = APIClient()
    response = client.post(
        "/api/v1/auth/password/reset/confirm/",
        {"uid": uid, "token": token, "new_password": "NewStrongPass123!"},
        format="json",
    )
    user.refresh_from_db()
    assert response.status_code == 200
    assert user.check_password("NewStrongPass123!")
