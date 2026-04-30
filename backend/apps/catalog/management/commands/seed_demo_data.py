"""Seed the application with demo content."""

from __future__ import annotations

import os
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.authentication.models import CustomUser
from apps.catalog.models import Category, Varietal, Wine, WineImage


class Command(BaseCommand):
    """Load demo catalog data for local development."""

    help = "Seed demo data for Bodega La Abeja."

    def handle(self, *args: object, **options: object) -> None:
        """Create baseline catalog and demo admin records."""
        demo_admin_email = os.getenv("DEMO_ADMIN_EMAIL", "admin@bodegalaabeja.com.ar").lower()
        demo_admin_password = os.getenv("DEMO_ADMIN_PASSWORD")

        tintos, _ = Category.objects.get_or_create(
            slug="vinos-tintos",
            defaults={
                "name": "Vinos Tintos",
                "description": "Selección emblemática de la bodega.",
                "order": 1,
            },
        )
        malbec, _ = Varietal.objects.get_or_create(
            slug="malbec",
            defaults={
                "name": "Malbec",
                "description": "Expresión clásica del sur mendocino.",
                "origin_region": "San Rafael",
            },
        )
        wine, created = Wine.objects.get_or_create(
            slug="gran-malbec-reserva",
            defaults={
                "name": "Gran Malbec Reserva",
                "category": tintos,
                "varietal": malbec,
                "vintage_year": 2022,
                "price": Decimal("18500.00"),
                "compare_at_price": Decimal("21000.00"),
                "cost_price": Decimal("9200.00"),
                "stock": 48,
                "sku": "LAB-MAL-2022-001",
                "alcohol_percentage": Decimal("14.2"),
                "serving_temperature_min": 16,
                "serving_temperature_max": 18,
                "ageing_months": 12,
                "ageing_type": Wine.AgeingType.OAK,
                "description": "Malbec de parcela con crianza equilibrada y perfil elegante.",
                "tasting_notes": "Ciruelas, violetas, cacao y final persistente.",
                "pairing_suggestions": ["Asado", "Risotto de hongos", "Quesos estacionados"],
                "winemaker_notes": "Fermentación parcelaria y crianza en roble francés.",
                "is_featured": True,
            },
        )
        if created:
            WineImage.objects.create(
                wine=wine,
                url="https://images.unsplash.com/photo-1516594915697-87eb3b1c14ea",
                alt_text="Botella de Gran Malbec Reserva",
                is_primary=True,
            )

        demo_admin, created = CustomUser.objects.get_or_create(
            email=demo_admin_email,
            defaults={
                "first_name": "Admin",
                "last_name": "La Abeja",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        demo_admin.is_staff = True
        demo_admin.is_superuser = True
        demo_admin.is_active = True
        if demo_admin_password:
            demo_admin.set_password(demo_admin_password)
        demo_admin.save(update_fields=["is_staff", "is_superuser", "is_active", "password"])

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Demo admin ready: {demo_admin_email}")
            )
        if not demo_admin_password:
            self.stdout.write(
                self.style.WARNING(
                    "DEMO_ADMIN_PASSWORD is not set. "
                    "The demo admin user was created without a known password."
                )
            )
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
