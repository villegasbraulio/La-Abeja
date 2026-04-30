"""Catalog filtering."""

from __future__ import annotations

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters

from .models import Wine


class WineFilter(filters.FilterSet):
    """Filter set for the catalog wine list."""

    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    category = filters.CharFilter(field_name="category__slug")
    varietal = filters.CharFilter(field_name="varietal__slug")
    vintage_year = filters.NumberFilter()
    vintage_min = filters.NumberFilter(field_name="vintage_year", lookup_expr="gte")
    vintage_max = filters.NumberFilter(field_name="vintage_year", lookup_expr="lte")
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    featured = filters.BooleanFilter(field_name="is_featured")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Wine
        fields = ["category", "varietal", "vintage_year", "in_stock", "featured"]

    def filter_in_stock(self, queryset: QuerySet[Wine], _: str, value: bool) -> QuerySet[Wine]:
        """Keep only wines with stock when requested."""
        if value:
            return queryset.filter(stock__gt=0)
        return queryset

    def filter_search(self, queryset: QuerySet[Wine], _: str, value: str) -> QuerySet[Wine]:
        """Search across name, description and varietal."""
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(varietal__name__icontains=value)
        )
