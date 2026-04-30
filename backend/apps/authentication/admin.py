"""Admin configuration for internal user management."""

from __future__ import annotations

from typing import cast

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import CustomUser


def _parse_lines_to_list(raw_value: str) -> list[str]:
    """Split a multiline text input into a clean list of strings."""
    return [line.strip() for line in raw_value.splitlines() if line.strip()]


class CustomUserChangeForm(forms.ModelForm):
    """Expose JSON preferences in a business-friendly format."""

    password = ReadOnlyPasswordHashField(
        label="Contraseña",
        help_text=(
            "Las contraseñas no se muestran en claro. "
            "Usa el flujo de cambio si necesitás actualizarla."
        ),
    )
    preferred_varietals_text = forms.CharField(
        label="Varietales preferidos",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Un varietal por línea. Ejemplo: Malbec",
    )

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "birth_date",
            "avatar",
            "newsletter_subscribed",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions",
            "cart_reminder_sent_at",
            "birthday_discount_sent_year",
            "last_review_request_sent_at",
        )

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Pre-fill the helper textarea from stored preferences."""
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["preferred_varietals_text"].initial = "\n".join(
                self.instance.preferred_varietals
            )

    def clean_preferred_varietals_text(self) -> list[str]:
        """Normalize preferred varietals into a simple list."""
        raw_value = self.cleaned_data["preferred_varietals_text"]
        return _parse_lines_to_list(raw_value)

    def clean_password(self) -> str:
        """Always return the initial password hash value."""
        return str(self.initial["password"])

    def save(self, commit: bool = True) -> CustomUser:
        """Persist helper preferences back to JSON."""
        instance = cast(CustomUser, super().save(commit=False))
        instance.preferred_varietals = self.cleaned_data["preferred_varietals_text"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CustomUserCreationForm(forms.ModelForm):
    """User creation form compatible with the custom email-based model."""

    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput,
    )
    preferred_varietals_text = forms.CharField(
        label="Varietales preferidos",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "birth_date",
            "avatar",
            "newsletter_subscribed",
            "is_staff",
            "is_active",
        )

    def clean_password2(self) -> str:
        """Ensure both password entries match."""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return str(password2)

    def clean_preferred_varietals_text(self) -> list[str]:
        """Normalize preferred varietals into a simple list."""
        raw_value = self.cleaned_data["preferred_varietals_text"]
        return _parse_lines_to_list(raw_value)

    def save(self, commit: bool = True) -> CustomUser:
        """Create a user with a properly hashed password."""
        instance = cast(CustomUser, super().save(commit=False))
        instance.set_password(self.cleaned_data["password1"])
        instance.preferred_varietals = self.cleaned_data["preferred_varietals_text"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Internal user admin with simpler labels and field grouping."""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = CustomUser
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "phone",
        "newsletter_subscribed",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active", "newsletter_subscribed", "date_joined")
    search_fields = ("email", "first_name", "last_name", "phone")
    readonly_fields = (
        "date_joined",
        "last_login",
        "cart_reminder_sent_at",
        "birthday_discount_sent_year",
        "last_review_request_sent_at",
    )
    fieldsets = (
        ("Acceso", {"fields": ("email", "password")}),
        (
            "Perfil",
            {
                "fields": (
                    ("first_name", "last_name"),
                    ("phone", "birth_date"),
                    "avatar",
                )
            },
        ),
        (
            "Preferencias",
            {"fields": ("newsletter_subscribed", "preferred_varietals_text")},
        ),
        (
            "Automatizaciones",
            {
                "fields": (
                    "cart_reminder_sent_at",
                    "birthday_discount_sent_year",
                    "last_review_request_sent_at",
                )
            },
        ),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    ("first_name", "last_name"),
                    ("phone", "birth_date"),
                    "avatar",
                    "preferred_varietals_text",
                    ("newsletter_subscribed", "is_staff", "is_active"),
                    ("password1", "password2"),
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")
    search_help_text = "Busca clientes o staff por email, nombre o teléfono."


admin.site.site_header = "Bodega La Abeja · Operaciones"
admin.site.site_title = "Bodega La Abeja Admin"
admin.site.index_title = "Panel interno para catálogo, clientes y tienda"
admin.site.empty_value_display = "—"
