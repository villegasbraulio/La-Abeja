"""Admin registrations for catalog models."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from django import forms
from django.contrib import admin
from django.db.models import Avg, Count, Q, QuerySet
from django.utils.html import format_html

from .models import Category, Review, Varietal, Wine, WineImage


def _parse_lines_to_list(raw_value: str) -> list[str]:
    """Split a multiline text input into a clean list of strings."""
    return [line.strip() for line in raw_value.splitlines() if line.strip()]


def _serialize_blends(blends: list[dict[str, object]]) -> str:
    """Return blend varietals in a human-editable multiline format."""
    lines: list[str] = []
    for blend in blends:
        varietal = str(blend.get("varietal", "")).strip()
        percentage = str(blend.get("percentage", "")).strip()
        if varietal:
            lines.append(f"{varietal}: {percentage}")
    return "\n".join(lines)


def _serialize_awards(awards: list[dict[str, object]]) -> str:
    """Return awards in a pipe-separated multiline format."""
    lines: list[str] = []
    for award in awards:
        label = str(award.get("award", "")).strip()
        score = str(award.get("score", "")).strip()
        year = str(award.get("year", "")).strip()
        if label:
            lines.append(f"{label} | {score} | {year}")
    return "\n".join(lines)


class StockHealthFilter(admin.SimpleListFilter):
    """Filter wines by stock health for operations users."""

    title = "salud de stock"
    parameter_name = "stock_health"

    def lookups(
        self,
        request: object,
        model_admin: admin.ModelAdmin[Wine],
    ) -> list[tuple[str, str]]:
        """Return the list of available stock states."""
        return [
            ("out", "Sin stock"),
            ("low", "Stock bajo"),
            ("ok", "Con stock saludable"),
        ]

    def queryset(self, request: object, queryset: QuerySet[Wine]) -> QuerySet[Wine]:
        """Apply the selected stock filter."""
        value = self.value()
        if value == "out":
            return queryset.filter(stock__lte=0)
        if value == "low":
            return queryset.filter(stock__gt=0, stock__lte=10)
        if value == "ok":
            return queryset.filter(stock__gt=10)
        return queryset


class WineAdminForm(forms.ModelForm):
    """Present JSON-heavy catalog fields in a friendlier format."""

    pairing_suggestions_text = forms.CharField(
        label="Maridajes sugeridos",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Un maridaje por línea. Ejemplo: Asado",
    )
    blend_varietals_text = forms.CharField(
        label="Composición del corte",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Una variedad por línea, usando 'Varietal: porcentaje'.",
    )
    awards_text = forms.CharField(
        label="Premios y puntajes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Una distinción por línea con formato 'Premio | puntaje | año'.",
    )

    class Meta:
        model = Wine
        fields = (
            "name",
            "slug",
            "category",
            "varietal",
            "vintage_year",
            "price",
            "compare_at_price",
            "cost_price",
            "stock",
            "low_stock_threshold",
            "sku",
            "alcohol_percentage",
            "serving_temperature_min",
            "serving_temperature_max",
            "ageing_months",
            "ageing_type",
            "tannins",
            "acidity",
            "body",
            "sweetness",
            "fruit_intensity",
            "description",
            "tasting_notes",
            "winemaker_notes",
            "meta_title",
            "meta_description",
            "is_featured",
            "is_active",
            "is_limited_edition",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "tasting_notes": forms.Textarea(attrs={"rows": 4}),
            "winemaker_notes": forms.Textarea(attrs={"rows": 4}),
            "meta_description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Pre-fill helper textareas from stored JSON values."""
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["pairing_suggestions_text"].initial = "\n".join(
                self.instance.pairing_suggestions
            )
            self.fields["blend_varietals_text"].initial = _serialize_blends(
                self.instance.blend_varietals
            )
            self.fields["awards_text"].initial = _serialize_awards(self.instance.awards)

    def clean_pairing_suggestions_text(self) -> list[str]:
        """Normalize maridajes into a plain list."""
        raw_value = self.cleaned_data["pairing_suggestions_text"]
        return _parse_lines_to_list(raw_value)

    def clean_blend_varietals_text(self) -> list[dict[str, object]]:
        """Parse the editable blend input into JSON storage."""
        raw_value = self.cleaned_data["blend_varietals_text"]
        entries: list[dict[str, object]] = []
        for line in _parse_lines_to_list(raw_value):
            if ":" not in line:
                raise forms.ValidationError(
                    "Usa el formato 'Varietal: porcentaje' en cada línea."
                )
            varietal, percentage = [part.strip() for part in line.split(":", maxsplit=1)]
            if not varietal or not percentage:
                raise forms.ValidationError(
                    "Cada línea del corte necesita varietal y porcentaje."
                )
            try:
                parsed_percentage = int(percentage)
            except ValueError as exc:
                raise forms.ValidationError("El porcentaje debe ser un número entero.") from exc
            entries.append({"varietal": varietal, "percentage": parsed_percentage})
        return entries

    def clean_awards_text(self) -> list[dict[str, object]]:
        """Parse the editable awards input into JSON storage."""
        raw_value = self.cleaned_data["awards_text"]
        entries: list[dict[str, object]] = []
        for line in _parse_lines_to_list(raw_value):
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 3:
                raise forms.ValidationError(
                    "Usa el formato 'Premio | puntaje | año' en cada línea."
                )
            award_label, score, year = parts
            if not award_label:
                raise forms.ValidationError("Cada premio necesita un nombre.")
            try:
                parsed_score = int(score)
                parsed_year = int(year)
            except ValueError as exc:
                raise forms.ValidationError(
                    "Puntaje y año deben ser números enteros."
                ) from exc
            entries.append({"award": award_label, "score": parsed_score, "year": parsed_year})
        return entries

    def save(self, commit: bool = True) -> Wine:
        """Persist helper fields back into the underlying JSON fields."""
        instance = cast(Wine, super().save(commit=False))
        instance.pairing_suggestions = self.cleaned_data["pairing_suggestions_text"]
        instance.blend_varietals = self.cleaned_data["blend_varietals_text"]
        instance.awards = self.cleaned_data["awards_text"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin with simpler merchandising controls."""

    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    search_fields = ("name", "slug")
    ordering = ("order", "name")
    prepopulated_fields = {"slug": ("name",)}
    search_help_text = "Buscar por nombre o slug."


@admin.register(Varietal)
class VarietalAdmin(admin.ModelAdmin):
    """Varietal admin optimized for catalog curation."""

    list_display = ("name", "slug", "origin_region")
    search_fields = ("name", "slug", "origin_region")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    search_help_text = "Buscar por varietal, slug u origen."


class WineImageInline(admin.TabularInline):
    """Inline image manager with previews."""

    model = WineImage
    extra = 1
    fields = ("preview", "url", "alt_text", "is_primary", "order")
    readonly_fields = ("preview",)

    @admin.display(description="Vista previa")
    def preview(self, obj: WineImage | None) -> str:
        """Render a small thumbnail for the current image."""
        if obj is None or not obj.url:
            return "Sin imagen"
        return format_html(
            (
                '<img src="{}" alt="{}" '
                'style="width: 84px; height: 84px; object-fit: cover; border-radius: 14px;" />'
            ),
            obj.url,
            obj.alt_text,
        )


@admin.register(Wine)
class WineAdmin(admin.ModelAdmin):
    """Friendly admin for the internal catalog team."""

    form = WineAdminForm
    inlines = [WineImageInline]
    list_display = (
        "thumbnail_preview",
        "name",
        "varietal",
        "category",
        "price",
        "stock_badge",
        "margin_badge",
        "is_featured",
        "is_active",
        "updated_at",
    )
    list_display_links = ("name",)
    list_editable = ("price", "is_featured", "is_active")
    list_filter = (
        "category",
        "varietal",
        "is_featured",
        "is_active",
        "is_limited_edition",
        StockHealthFilter,
    )
    search_fields = ("name", "sku", "slug")
    ordering = ("-is_featured", "name")
    autocomplete_fields = ("category", "varietal")
    list_select_related = ("category", "varietal")
    prepopulated_fields = {"slug": ("name",)}
    save_on_top = True
    list_per_page = 20
    search_help_text = "Busca vinos por nombre, SKU o slug."
    readonly_fields = (
        "primary_image_preview",
        "stock_health_display",
        "margin_display",
        "review_snapshot",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Resumen comercial",
            {
                "fields": (
                    ("name", "slug"),
                    ("sku", "vintage_year"),
                    ("category", "varietal"),
                    ("is_active", "is_featured", "is_limited_edition"),
                    "primary_image_preview",
                )
            },
        ),
        (
            "Precio, margen y stock",
            {
                "fields": (
                    ("price", "compare_at_price", "cost_price"),
                    ("stock", "low_stock_threshold"),
                    ("stock_health_display", "margin_display"),
                )
            },
        ),
        (
            "Ficha del vino",
            {
                "fields": (
                    "description",
                    "tasting_notes",
                    "winemaker_notes",
                    "pairing_suggestions_text",
                    "blend_varietals_text",
                    "awards_text",
                    "review_snapshot",
                )
            },
        ),
        (
            "Servicio y perfil sensorial",
            {
                "fields": (
                    ("alcohol_percentage", "ageing_months", "ageing_type"),
                    ("serving_temperature_min", "serving_temperature_max"),
                    ("tannins", "acidity", "body"),
                    ("sweetness", "fruit_intensity"),
                )
            },
        ),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": ("meta_title", "meta_description"),
            },
        ),
        (
            "Trazabilidad",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    actions = (
        "activate_selected",
        "deactivate_selected",
        "mark_as_featured",
        "remove_featured_flag",
    )

    def get_queryset(self, request: object) -> QuerySet[Wine]:
        """Load related objects and aggregate review stats for the changelist."""
        queryset = (
            super()
            .get_queryset(request)
            .select_related("category", "varietal")
            .prefetch_related("images")
            .annotate(
                approved_review_count=Count("reviews", filter=Q(reviews__is_approved=True)),
                approved_review_avg=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
            )
        )
        return cast(QuerySet[Wine], queryset)

    @admin.display(description="Imagen")
    def thumbnail_preview(self, obj: Wine) -> str:
        """Render the first image in the changelist."""
        primary_image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if primary_image is None:
            return "Sin imagen"
        return format_html(
            '<img src="{}" alt="{}" class="bodega-admin-thumb" />',
            primary_image.url,
            obj.name,
        )

    @admin.display(description="Portada actual")
    def primary_image_preview(self, obj: Wine) -> str:
        """Render the primary image on the detail page."""
        primary_image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if primary_image is None:
            return "Todavía no cargaste imágenes."
        return format_html(
            '<div class="bodega-admin-hero">'
            '<img src="{}" alt="{}" class="bodega-admin-hero__image" />'
            '<div><strong>{}</strong><br /><span>{}</span></div>'
            "</div>",
            primary_image.url,
            obj.name,
            obj.name,
            primary_image.alt_text,
        )

    @admin.display(description="Estado de stock")
    def stock_badge(self, obj: Wine) -> str:
        """Render a badge describing stock status on the list page."""
        if obj.stock <= 0:
            badge_class = "danger"
            label = "Sin stock"
        elif obj.stock <= obj.low_stock_threshold:
            badge_class = "warning"
            label = f"Bajo ({obj.stock})"
        else:
            badge_class = "success"
            label = f"OK ({obj.stock})"
        return format_html(
            '<span class="bodega-badge bodega-badge--{}">{}</span>',
            badge_class,
            label,
        )

    @admin.display(description="Estado de stock")
    def stock_health_display(self, obj: Wine) -> str:
        """Render a more descriptive stock summary on the detail page."""
        return format_html(
            "{}<div class='help'>Umbral configurado: {} unidades.</div>",
            self.stock_badge(obj),
            obj.low_stock_threshold,
        )

    @admin.display(description="Margen estimado")
    def margin_badge(self, obj: Wine) -> str:
        """Render a gross margin preview on the list page."""
        if obj.price <= 0:
            return "Sin calcular"
        margin = ((obj.price - obj.cost_price) / obj.price) * Decimal("100")
        formatted_margin = f"{margin:.0f}%"
        return format_html(
            '<span class="bodega-badge bodega-badge--neutral">{}</span>',
            formatted_margin,
        )

    @admin.display(description="Margen estimado")
    def margin_display(self, obj: Wine) -> str:
        """Render the estimated gross margin with context."""
        if obj.price <= 0:
            return "No se puede calcular con precio igual a cero."
        margin = ((obj.price - obj.cost_price) / obj.price) * Decimal("100")
        return (
            f"{margin:.0f}% de margen bruto estimado "
            f"(precio ${obj.price} vs costo ${obj.cost_price})."
        )

    @admin.display(description="Reviews aprobadas")
    def review_snapshot(self, obj: Wine) -> str:
        """Show the approved review count and average rating."""
        review_count = getattr(obj, "approved_review_count", 0)
        average = getattr(obj, "approved_review_avg", None)
        if not review_count or average is None:
            return "Todavía no hay reviews aprobadas."
        return f"{review_count} reviews aprobadas · promedio {average:.1f}/5"

    @admin.action(description="Activar vinos seleccionados")
    def activate_selected(self, request: object, queryset: QuerySet[Wine]) -> None:
        """Bulk activate wines."""
        queryset.update(is_active=True)

    @admin.action(description="Desactivar vinos seleccionados")
    def deactivate_selected(self, request: object, queryset: QuerySet[Wine]) -> None:
        """Bulk deactivate wines."""
        queryset.update(is_active=False)

    @admin.action(description="Marcar como destacados")
    def mark_as_featured(self, request: object, queryset: QuerySet[Wine]) -> None:
        """Bulk mark wines as featured."""
        queryset.update(is_featured=True)

    @admin.action(description="Quitar de destacados")
    def remove_featured_flag(self, request: object, queryset: QuerySet[Wine]) -> None:
        """Bulk remove featured status."""
        queryset.update(is_featured=False)

    class Media:
        """Inject the branded admin stylesheet."""

        css = {"all": ("admin/css/bodega_admin.css",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review moderation admin with simple approval actions."""

    list_display = ("wine", "user", "rating", "is_approved", "is_verified_purchase", "created_at")
    list_filter = ("is_approved", "is_verified_purchase", "rating", "created_at")
    search_fields = ("wine__name", "user__email", "title", "body")
    autocomplete_fields = ("wine", "user")
    readonly_fields = ("created_at",)
    actions = ("approve_reviews", "hide_reviews")
    search_help_text = "Busca reviews por vino, cliente o contenido."

    @admin.action(description="Aprobar reviews seleccionadas")
    def approve_reviews(self, request: object, queryset: QuerySet[Review]) -> None:
        """Bulk approve selected reviews."""
        queryset.update(is_approved=True)

    @admin.action(description="Ocultar reviews seleccionadas")
    def hide_reviews(self, request: object, queryset: QuerySet[Review]) -> None:
        """Bulk hide selected reviews."""
        queryset.update(is_approved=False)
