"""Permissions for AI API endpoints."""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class IsStaffOrReadOnlyConversation(BasePermission):
    """Allow staff broad access while customers can access their own conversations."""

    def has_object_permission(self, request: Request, view: View, obj: object) -> bool:
        """Grant access to staff or the owning customer."""
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return getattr(obj, "customer_id", None) == user.id
