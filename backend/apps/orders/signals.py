"""Order signals."""

from __future__ import annotations

import structlog
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.catalog.models import Wine

from .models import Order

logger = structlog.get_logger(__name__)


@receiver(pre_save, sender=Order)
def cache_previous_order_status(
    sender: type[Order],
    instance: Order,
    **kwargs: object,
) -> None:
    """Keep track of the previous status before saving."""
    _ = sender, kwargs
    if instance.pk:
        previous = Order.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        instance._previous_status = previous
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def order_post_save(
    sender: type[Order],
    instance: Order,
    created: bool,
    **kwargs: object,
) -> None:
    """Trigger stock and notification side effects."""
    _ = sender, kwargs
    if created:
        for item in instance.items.select_related("wine").all():
            Wine.objects.filter(id=item.wine_id).update(stock=models.F("stock") - item.quantity)
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status and previous_status != instance.status:
        logger.info("order_status_changed", order_id=str(instance.id), status=instance.status)
