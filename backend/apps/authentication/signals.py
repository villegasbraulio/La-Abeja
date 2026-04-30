"""Authentication signals."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

User = get_user_model()


@receiver(pre_save, sender=User)
def normalize_user_email(sender: type[User], instance: User, **kwargs: object) -> None:
    """Ensure emails are persisted in lowercase."""
    instance.email = instance.email.lower()
