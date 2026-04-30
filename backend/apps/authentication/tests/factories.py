"""Authentication factories."""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for custom users."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = "+5492604000000"
    newsletter_subscribed = True

    @factory.post_generation
    def password(self, create: bool, extracted: str | None, **kwargs: object) -> None:
        """Hash and persist the password after instance creation."""
        raw_password = extracted or "StrongPass123!"
        self.set_password(raw_password)
        if create:
            self.save(update_fields=["password"])
