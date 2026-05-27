"""Catalog-oriented tools."""

from __future__ import annotations

from django.db.models import Q

from apps.catalog.models import Wine

from .base import ToolContext


def search_catalog(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Search the product catalog by text."""
    del context
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"results": []}
    wines = (
        Wine.objects.select_related("category", "varietal")
        .filter(
            Q(is_active=True),
            Q(name__icontains=query)
            | Q(varietal__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(description__icontains=query)
            | Q(tasting_notes__icontains=query),
        )
        .order_by("-is_featured", "name")[:5]
    )
    return {
        "results": [
            {
                "id": str(wine.id),
                "name": wine.name,
                "slug": wine.slug,
                "varietal": wine.varietal.name,
                "category": wine.category.name,
                "price": str(wine.price),
                "in_stock": wine.stock > 0,
                "stock": wine.stock,
            }
            for wine in wines
        ]
    }


def get_stock_snapshot(payload: dict[str, object], context: ToolContext) -> dict[str, object]:
    """Return stock information for a single SKU or slug."""
    del context
    sku = str(payload.get("sku") or "").strip()
    slug = str(payload.get("slug") or "").strip()
    wine = Wine.objects.filter(Q(sku__iexact=sku) | Q(slug__iexact=slug), is_active=True).first()
    if wine is None:
        return {"found": False}
    return {
        "found": True,
        "id": str(wine.id),
        "name": wine.name,
        "sku": wine.sku,
        "slug": wine.slug,
        "stock": wine.stock,
        "low_stock_threshold": wine.low_stock_threshold,
        "in_stock": wine.stock > 0,
    }
