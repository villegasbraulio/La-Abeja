"""Factories for payment records."""

from __future__ import annotations

from decimal import Decimal

import factory

from apps.orders.tests.factories import OrderFactory

from ..models import Payment


class PaymentFactory(factory.django.DjangoModelFactory):
    """Factory for payments."""

    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    mp_preference_id = factory.Sequence(lambda n: f"pref_{n}")
    status = Payment.Status.PENDING
    amount = Decimal("8000.00")
    currency = "ARS"
