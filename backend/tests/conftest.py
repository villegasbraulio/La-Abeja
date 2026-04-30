"""Global pytest fixtures."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.tests.factories import UserFactory
from apps.catalog.tests.factories import WineFactory


@pytest.fixture
def api_client() -> APIClient:
    """Return an unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client() -> tuple[APIClient, object]:
    """Return an authenticated API client and the user behind it."""
    user = UserFactory()
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, user


@pytest.fixture
def user_factory():
    """Expose the user factory to tests."""
    return UserFactory


@pytest.fixture
def wine_factory():
    """Expose the wine factory to tests."""
    return WineFactory
