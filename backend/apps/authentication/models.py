"""Authentication models."""

from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Email-based user model for shoppers and staff."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.URLField(blank=True)
    preferred_varietals = models.JSONField(default=list, blank=True)
    newsletter_subscribed = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    cart_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    birthday_discount_sent_year = models.IntegerField(null=True, blank=True)
    last_review_request_sent_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        """Return the user's email for admin displays."""
        return self.email

    @property
    def full_name(self) -> str:
        """Return the user's full display name."""
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args: object, **kwargs: object) -> None:
        """Normalize email casing before persisting."""
        self.email = self.email.lower()
        super().save(*args, **kwargs)
