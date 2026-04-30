"""Authentication-specific permissions."""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class IsCurrentUserOrStaff(BasePermission):
    """Allow users to edit themselves while staff can access any record."""

    def has_object_permission(self, request: Request, view: View, obj: object) -> bool:
        """Grant access if the request user owns the object or is staff."""
        if not request.user.is_authenticated:
            return False
        return bool(request.user.is_staff or getattr(obj, "id", None) == request.user.id)


class IsStaffUser(BasePermission):
    """Restrict access to internal staff members."""

    def has_permission(self, request: Request, view: View) -> bool:
        """Grant access only to authenticated staff users."""
        return bool(request.user.is_authenticated and request.user.is_staff)
