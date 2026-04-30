"""Custom user managers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from .models import CustomUser


class CustomUserManager(BaseUserManager):
    """Manager for the email-based custom user model."""

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> CustomUser:
        """Create and persist a standard user."""
        if not email:
            raise ValueError("Email is required.")

        normalized_email = self.normalize_email(email).lower()
        user = self.model(email=normalized_email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> CustomUser:
        """Create and persist a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email=email, password=password, **extra_fields)
