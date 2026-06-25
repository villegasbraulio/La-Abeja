"""Celery configuration."""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("bodega_la_abeja")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-abandoned-carts": {
        "task": "apps.automations.tasks.cart_tasks.check_abandoned_carts",
        "schedule": crontab(minute="*/15"),
    },
    "send-birthday-discounts": {
        "task": "apps.automations.tasks.marketing_tasks.send_birthday_discounts",
        "schedule": crontab(hour=9, minute=0),
    },
    "dispatch-transactional-outbox": {
        "task": "apps.automations.tasks.outbox_tasks.dispatch_pending_outbox_events",
        "schedule": crontab(minute="*"),
    },
    "expire-booking-holds": {
        "task": "apps.automations.tasks.reconciliation_tasks.expire_pending_booking_holds_task",
        "schedule": crontab(minute="*"),
    },
    "reconcile-payments-and-shipments": {
        "task": "apps.automations.tasks.reconciliation_tasks.reconcile_external_operations",
        "schedule": crontab(minute="*/10"),
    },
}
