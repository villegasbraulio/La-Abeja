"""Authentication model tests."""

from __future__ import annotations

import pytest

from apps.authentication.tests.factories import UserFactory


@pytest.mark.django_db
def test_user_email_is_normalized() -> None:
    """Emails should be saved in lowercase."""
    user = UserFactory(email="UPPER@Example.COM")
    assert user.email == "upper@example.com"


@pytest.mark.django_db
def test_create_superuser_flags() -> None:
    """Superusers should be staff and superusers."""
    user_model = UserFactory._meta.model
    admin = user_model.objects.create_superuser(
        email="admin@example.com",
        password="StrongPass123!",
        first_name="Admin",
        last_name="User",
    )
    assert admin.is_staff is True
    assert admin.is_superuser is True
