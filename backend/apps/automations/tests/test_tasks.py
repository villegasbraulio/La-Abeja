"""Automation task tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.authentication.tests.factories import UserFactory
from apps.automations.tasks.cart_tasks import check_abandoned_carts
from apps.automations.tasks.marketing_tasks import send_birthday_discounts
from apps.catalog.tests.factories import WineFactory
from apps.orders.models import Cart, CartItem, PromoCode


@pytest.mark.django_db
class TestAbandonedCartTask:
    """Coverage for abandoned cart automations."""

    @patch("apps.automations.tasks.cart_tasks.EmailService.send_transactional")
    def test_sends_email_for_abandoned_cart(self, mock_email) -> None:
        """Abandoned carts with items should trigger an email."""
        user = UserFactory()
        wine = WineFactory(is_active=True, stock=10)
        cart = Cart.objects.create(
            user=user,
            last_activity_at=timezone.now() - timedelta(hours=2),
        )
        CartItem.objects.create(cart=cart, wine=wine, quantity=1, unit_price=wine.price)

        result = check_abandoned_carts()

        assert result["emails_sent"] == 1
        mock_email.assert_called_once()
        cart.refresh_from_db()
        assert cart.abandon_reminder_sent is True

    @patch("apps.automations.tasks.cart_tasks.EmailService.send_transactional")
    def test_does_not_resend_to_same_cart(self, mock_email) -> None:
        """Already reminded carts should be ignored."""
        user = UserFactory()
        Cart.objects.create(
            user=user,
            last_activity_at=timezone.now() - timedelta(hours=3),
            abandon_reminder_sent=True,
        )

        result = check_abandoned_carts()

        assert result["emails_sent"] == 0
        mock_email.assert_not_called()


@pytest.mark.django_db
class TestBirthdayDiscountTask:
    """Coverage for birthday marketing automation."""

    @patch("apps.automations.tasks.marketing_tasks.EmailService.send_transactional")
    def test_sends_discount_to_birthday_users(self, mock_email) -> None:
        """Subscribed users with birthdays today should get a code."""
        today = timezone.localdate()
        user = UserFactory(birth_date=today.replace(year=1990), newsletter_subscribed=True)

        result = send_birthday_discounts()

        assert result["birthday_emails_sent"] == 1
        assert PromoCode.objects.filter(code__startswith="CUMPLE").count() == 1
        user.refresh_from_db()
        assert user.birthday_discount_sent_year == today.year
        mock_email.assert_called_once()
