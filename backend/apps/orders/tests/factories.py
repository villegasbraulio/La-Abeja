"""Factories for orders and order items."""

from __future__ import annotations

from decimal import Decimal

import factory

from apps.authentication.tests.factories import UserFactory
from apps.catalog.tests.factories import WineFactory

from ..models import Order, OrderItem


class OrderFactory(factory.django.DjangoModelFactory):
    """Factory for orders."""

    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = Order.Status.PENDING_PAYMENT
    subtotal = Decimal("4500.00")
    discount_amount = Decimal("0.00")
    shipping_cost = Decimal("3500.00")
    total = Decimal("8000.00")
    shipping_method = Order.ShippingMethod.STANDARD
    shipping_address = {
        "recipient_name": "Maria Perez",
        "street": "Av. San Martin",
        "number": "1234",
        "floor_apt": "",
        "city": "San Rafael",
        "province": "Mendoza",
        "postal_code": "5600",
        "country": "Argentina",
        "phone": "+5492604000000",
    }


class OrderItemFactory(factory.django.DjangoModelFactory):
    """Factory for order line items."""

    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    wine = factory.SubFactory(WineFactory)
    wine_name = factory.SelfAttribute("wine.name")
    wine_sku = factory.SelfAttribute("wine.sku")
    quantity = 1
    unit_price = Decimal("4500.00")
    subtotal = Decimal("4500.00")
