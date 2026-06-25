"""Seed the application with a complete, repeatable demo dataset."""

from __future__ import annotations

import os
from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import CustomUser
from apps.catalog.models import Category, Varietal, Wine, WineImage
from apps.orders.models import PromoCode
from apps.reservations.models import Experience, TimeSlot

CATEGORIES = (
    ("vinos-tintos", "Vinos Tintos", "Tintos con identidad sanrafaelina.", "wine", 1),
    ("vinos-blancos", "Vinos Blancos", "Blancos frescos, minerales y aromáticos.", "sun", 2),
    (
        "vinos-rosados",
        "Vinos Rosados",
        "Rosados vibrantes para disfrutar todo el año.",
        "sparkles",
        3,
    ),
    ("espumantes", "Espumantes", "Burbujas elaboradas por método tradicional.", "glass", 4),
    (
        "ediciones-especiales",
        "Ediciones Especiales",
        "Partidas limitadas y vinos de colección.",
        "star",
        5,
    ),
)

VARIETALS = (
    ("malbec", "Malbec", "Fruta negra, violetas y taninos sedosos.", "San Rafael"),
    ("cabernet-sauvignon", "Cabernet Sauvignon", "Estructura y carácter especiado.", "San Rafael"),
    ("bonarda", "Bonarda", "Frutal, jugosa y de gran frescura.", "Valle de Uco"),
    ("chardonnay", "Chardonnay", "Cítricos, flores blancas y textura envolvente.", "San Rafael"),
    ("chenin-blanc", "Chenin Blanc", "Aromática, fresca y delicadamente floral.", "San Rafael"),
)

WINES = (
    {
        "slug": "gran-malbec-reserva",
        "name": "Gran Malbec Reserva",
        "category": "vinos-tintos",
        "varietal": "malbec",
        "vintage_year": 2022,
        "price": "18500.00",
        "compare_at_price": "21000.00",
        "cost_price": "9200.00",
        "stock": 48,
        "sku": "LAB-MAL-2022-001",
        "alcohol_percentage": "14.2",
        "temperatures": (16, 18),
        "ageing_months": 12,
        "ageing_type": Wine.AgeingType.OAK,
        "profile": (72, 52, 78, 18, 82),
        "description": "Malbec de parcela con crianza equilibrada y perfil elegante.",
        "tasting_notes": "Ciruelas, violetas, cacao y final persistente.",
        "pairings": ["Asado", "Risotto de hongos", "Quesos estacionados"],
        "winemaker_notes": "Fermentación parcelaria y crianza en roble francés.",
        "awards": [{"award": "Guía Descorchados", "score": 92, "year": 2024}],
        "is_featured": True,
        "is_limited_edition": False,
        "image": "https://images.unsplash.com/photo-1516594915697-87eb3b1c14ea",
    },
    {
        "slug": "cabernet-finca-la-abeja",
        "name": "Cabernet Finca La Abeja",
        "category": "vinos-tintos",
        "varietal": "cabernet-sauvignon",
        "vintage_year": 2021,
        "price": "16700.00",
        "compare_at_price": "18900.00",
        "cost_price": "8100.00",
        "stock": 36,
        "sku": "LAB-CAB-2021-002",
        "alcohol_percentage": "14.0",
        "temperatures": (16, 18),
        "ageing_months": 10,
        "ageing_type": Wine.AgeingType.OAK,
        "profile": (82, 58, 84, 14, 68),
        "description": "Cabernet de viñedos históricos, profundo y especiado.",
        "tasting_notes": "Cassis, pimiento asado, pimienta negra y cedro.",
        "pairings": ["Ojo de bife", "Cordero", "Provoleta"],
        "winemaker_notes": "Cosecha manual y crianza en barricas de segundo uso.",
        "awards": [{"award": "Argentina Wine Awards", "score": 91, "year": 2023}],
        "is_featured": True,
        "is_limited_edition": False,
        "image": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb",
    },
    {
        "slug": "bonarda-joven",
        "name": "Bonarda Joven",
        "category": "vinos-tintos",
        "varietal": "bonarda",
        "vintage_year": 2024,
        "price": "9800.00",
        "compare_at_price": None,
        "cost_price": "4700.00",
        "stock": 72,
        "sku": "LAB-BON-2024-003",
        "alcohol_percentage": "13.4",
        "temperatures": (14, 16),
        "ageing_months": 6,
        "ageing_type": Wine.AgeingType.CEMENT,
        "profile": (46, 64, 56, 22, 88),
        "description": "Un tinto joven, jugoso y versátil para todos los días.",
        "tasting_notes": "Cereza madura, frambuesa y un sutil recuerdo herbal.",
        "pairings": ["Empanadas", "Pastas", "Pizza a la piedra"],
        "winemaker_notes": "Fermentado y criado en huevos de hormigón.",
        "awards": [],
        "is_featured": False,
        "is_limited_edition": False,
        "image": "https://images.unsplash.com/photo-1473973266408-ed4e27abdd47",
    },
    {
        "slug": "chardonnay-altos-del-atuel",
        "name": "Chardonnay Altos del Atuel",
        "category": "vinos-blancos",
        "varietal": "chardonnay",
        "vintage_year": 2024,
        "price": "12400.00",
        "compare_at_price": "13900.00",
        "cost_price": "5900.00",
        "stock": 54,
        "sku": "LAB-CHA-2024-004",
        "alcohol_percentage": "13.2",
        "temperatures": (8, 10),
        "ageing_months": 4,
        "ageing_type": Wine.AgeingType.STAINLESS,
        "profile": (8, 78, 48, 28, 74),
        "description": "Blanco de altura con tensión, frescura y textura cremosa.",
        "tasting_notes": "Pera, lima, flores blancas y una nota mineral.",
        "pairings": ["Trucha", "Ceviche", "Quesos blandos"],
        "winemaker_notes": "Trabajo sobre lías finas durante cuatro meses.",
        "awards": [{"award": "Tim Atkin Argentina", "score": 90, "year": 2025}],
        "is_featured": True,
        "is_limited_edition": False,
        "image": "https://images.unsplash.com/photo-1558001373-7b93ee48ffa0",
    },
    {
        "slug": "espumante-chenin-brut-nature",
        "name": "Espumante Chenin Brut Nature",
        "category": "espumantes",
        "varietal": "chenin-blanc",
        "vintage_year": 2023,
        "price": "19500.00",
        "compare_at_price": "22000.00",
        "cost_price": "9800.00",
        "stock": 24,
        "sku": "LAB-CHE-2023-005",
        "alcohol_percentage": "12.3",
        "temperatures": (6, 8),
        "ageing_months": 18,
        "ageing_type": Wine.AgeingType.STAINLESS,
        "profile": (4, 84, 44, 10, 66),
        "description": "Espumante de método tradicional, seco y de burbuja fina.",
        "tasting_notes": "Manzana verde, pan brioche, almendras y final cítrico.",
        "pairings": ["Ostras", "Sushi", "Aperitivos"],
        "winemaker_notes": "Segunda fermentación en botella y 18 meses sobre lías.",
        "awards": [{"award": "Vinomanos", "score": 93, "year": 2025}],
        "is_featured": True,
        "is_limited_edition": True,
        "image": "https://images.unsplash.com/photo-1547595628-c61a29f496f0",
    },
)

EXPERIENCES = (
    {
        "slug": "tour-historico-la-abeja",
        "name": "Tour Histórico La Abeja",
        "experience_type": Experience.ExperienceType.WINERY_TOUR,
        "description": "Un recorrido por la primera bodega de San Rafael y sus vinos.",
        "duration_minutes": 75,
        "price_per_person": "12000.00",
        "min_guests": 1,
        "max_guests": 18,
        "includes": ["Recorrido guiado", "Degustación de 3 vinos", "Agua mineral"],
        "highlights": ["Edificio histórico", "Sala de barricas", "Jardines"],
        "cover_image": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb",
        "is_featured": True,
    },
    {
        "slug": "cata-premium-reservas",
        "name": "Cata Premium de Reservas",
        "experience_type": Experience.ExperienceType.PREMIUM_TASTING,
        "description": "Degustación íntima de etiquetas reserva y partidas limitadas.",
        "duration_minutes": 90,
        "price_per_person": "28000.00",
        "min_guests": 2,
        "max_guests": 12,
        "includes": ["5 vinos premium", "Tabla de quesos", "Sommelier dedicado"],
        "highlights": ["Cava privada", "Copas de cristal", "Ediciones limitadas"],
        "cover_image": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3",
        "is_featured": True,
    },
    {
        "slug": "vendimia-por-un-dia",
        "name": "Vendimia por un Día",
        "experience_type": Experience.ExperienceType.HARVEST,
        "description": "Una jornada de cosecha, molienda y celebración entre viñedos.",
        "duration_minutes": 180,
        "price_per_person": "42000.00",
        "min_guests": 4,
        "max_guests": 20,
        "includes": ["Kit de cosecha", "Almuerzo regional", "Vino de la casa"],
        "highlights": ["Cosecha manual", "Pisada de uvas", "Almuerzo al aire libre"],
        "cover_image": "https://images.unsplash.com/photo-1464638681273-096c166ab676",
        "is_featured": True,
    },
    {
        "slug": "evento-privado-en-la-cava",
        "name": "Evento Privado en la Cava",
        "experience_type": Experience.ExperienceType.PRIVATE_EVENT,
        "description": "La cava histórica reservada para celebraciones y encuentros.",
        "duration_minutes": 240,
        "price_per_person": "55000.00",
        "min_guests": 8,
        "max_guests": 30,
        "includes": ["Uso exclusivo", "Recepción", "Menú de tres pasos"],
        "highlights": ["Ambientación personalizada", "Anfitrión privado", "Cava histórica"],
        "cover_image": "https://images.unsplash.com/photo-1527529482837-4698179dc6ce",
        "is_featured": False,
    },
    {
        "slug": "maridaje-con-chef",
        "name": "Maridaje con Chef",
        "experience_type": Experience.ExperienceType.WINE_PAIRING,
        "description": "Cinco pasos de cocina mendocina maridados con vinos de la bodega.",
        "duration_minutes": 150,
        "price_per_person": "48000.00",
        "min_guests": 2,
        "max_guests": 16,
        "includes": ["Menú de cinco pasos", "5 vinos", "Café y petit fours"],
        "highlights": ["Cocina de estación", "Mesa del chef", "Maridaje comentado"],
        "cover_image": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0",
        "is_featured": True,
    },
)


class Command(BaseCommand):
    """Load master data and realistic demo content for local development."""

    help = "Seed at least five records for every configurable business area."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Create or refresh demo data without duplicating natural keys."""
        categories = self._seed_categories()
        varietals = self._seed_varietals()
        wines = self._seed_wines(categories, varietals)
        self._seed_promotions()
        self._seed_experiences()
        self._seed_admin()

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready: "
                f"{Category.objects.count()} categories, "
                f"{Varietal.objects.count()} varietals, "
                f"{len(wines)} seeded wines, "
                f"{PromoCode.objects.count()} promotions, "
                f"{Experience.objects.count()} experiences and "
                f"{TimeSlot.objects.count()} time slots."
            )
        )

    def _seed_categories(self) -> dict[str, Category]:
        result = {}
        for slug, name, description, icon, order in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "icon": icon,
                    "order": order,
                },
            )
            result[slug] = category
        return result

    def _seed_varietals(self) -> dict[str, Varietal]:
        result = {}
        for slug, name, description, origin_region in VARIETALS:
            varietal, _ = Varietal.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "origin_region": origin_region,
                },
            )
            result[slug] = varietal
        return result

    def _seed_wines(
        self,
        categories: dict[str, Category],
        varietals: dict[str, Varietal],
    ) -> list[Wine]:
        result = []
        for data in WINES:
            tannins, acidity, body, sweetness, fruit_intensity = data["profile"]
            temperature_min, temperature_max = data["temperatures"]
            wine, _ = Wine.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "category": categories[data["category"]],
                    "varietal": varietals[data["varietal"]],
                    "vintage_year": data["vintage_year"],
                    "price": Decimal(data["price"]),
                    "compare_at_price": (
                        Decimal(data["compare_at_price"])
                        if data["compare_at_price"]
                        else None
                    ),
                    "cost_price": Decimal(data["cost_price"]),
                    "stock": data["stock"],
                    "low_stock_threshold": 10,
                    "sku": data["sku"],
                    "alcohol_percentage": Decimal(data["alcohol_percentage"]),
                    "serving_temperature_min": temperature_min,
                    "serving_temperature_max": temperature_max,
                    "ageing_months": data["ageing_months"],
                    "ageing_type": data["ageing_type"],
                    "tannins": tannins,
                    "acidity": acidity,
                    "body": body,
                    "sweetness": sweetness,
                    "fruit_intensity": fruit_intensity,
                    "description": data["description"],
                    "tasting_notes": data["tasting_notes"],
                    "pairing_suggestions": data["pairings"],
                    "winemaker_notes": data["winemaker_notes"],
                    "awards": data["awards"],
                    "meta_title": f"{data['name']} | Bodega La Abeja",
                    "meta_description": data["description"],
                    "is_featured": data["is_featured"],
                    "is_active": True,
                    "is_limited_edition": data["is_limited_edition"],
                },
            )
            WineImage.objects.update_or_create(
                wine=wine,
                order=0,
                defaults={
                    "url": data["image"],
                    "alt_text": f"Botella de {data['name']}",
                    "is_primary": True,
                },
            )
            result.append(wine)
        return result

    def _seed_promotions(self) -> None:
        now = timezone.now()
        promotions = (
            ("BIENVENIDA15", PromoCode.DiscountType.PERCENTAGE, "15.00", "25000.00", 500),
            ("ABEJA10", PromoCode.DiscountType.PERCENTAGE, "10.00", "15000.00", None),
            ("VENDIMIA5000", PromoCode.DiscountType.FIXED, "5000.00", "40000.00", 200),
            ("ENVIOGRATIS", PromoCode.DiscountType.FREE_SHIPPING, "0.00", "30000.00", 300),
            ("CLUB20", PromoCode.DiscountType.PERCENTAGE, "20.00", "60000.00", 100),
        )
        for code, discount_type, value, minimum, max_uses in promotions:
            PromoCode.objects.update_or_create(
                code=code,
                defaults={
                    "discount_type": discount_type,
                    "discount_value": Decimal(value),
                    "min_order_amount": Decimal(minimum),
                    "max_uses": max_uses,
                    "valid_from": now - timedelta(days=30),
                    "valid_until": now + timedelta(days=365),
                    "is_active": True,
                },
            )

    def _seed_experiences(self) -> None:
        today = timezone.localdate()
        first_slot_date = today + timedelta(days=1)
        guides = ("Lucía", "Martín", "Sofía", "Tomás", "Valentina")
        start_times = (time(10, 0), time(11, 30), time(15, 0), time(16, 30), time(18, 0))

        for data in EXPERIENCES:
            experience, _ = Experience.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "experience_type": data["experience_type"],
                    "description": data["description"],
                    "duration_minutes": data["duration_minutes"],
                    "price_per_person": Decimal(data["price_per_person"]),
                    "min_guests": data["min_guests"],
                    "max_guests": data["max_guests"],
                    "includes": data["includes"],
                    "highlights": data["highlights"],
                    "cover_image": data["cover_image"],
                    "gallery_images": [],
                    "cancellation_hours": 24,
                    "is_active": True,
                    "is_featured": data["is_featured"],
                },
            )
            for offset, (guide, start_time) in enumerate(zip(guides, start_times, strict=True)):
                slot_date = first_slot_date + timedelta(days=offset)
                end_datetime = timezone.datetime.combine(slot_date, start_time) + timedelta(
                    minutes=data["duration_minutes"]
                )
                TimeSlot.objects.update_or_create(
                    experience=experience,
                    date=slot_date,
                    start_time=start_time,
                    defaults={
                        "end_time": end_datetime.time(),
                        "capacity": data["max_guests"],
                        "spots_available": data["max_guests"],
                        "guide_name": guide,
                        "is_blocked": False,
                        "block_reason": "",
                    },
                )

    def _seed_admin(self) -> None:
        email = os.getenv("DEMO_ADMIN_EMAIL", "admin@bodegalaabeja.com.ar").lower()
        password = os.getenv("DEMO_ADMIN_PASSWORD")
        admin, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={"first_name": "Admin", "last_name": "La Abeja"},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        update_fields = ["is_staff", "is_superuser", "is_active"]
        if password:
            admin.set_password(password)
            update_fields.append("password")
        admin.save(update_fields=update_fields)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Demo admin ready: {email}"))
        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "DEMO_ADMIN_PASSWORD is not set; the admin password was left unchanged."
                )
            )
