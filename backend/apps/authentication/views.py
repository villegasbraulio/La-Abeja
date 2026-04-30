"""Authentication API views."""

from __future__ import annotations

import structlog
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.notifications.email import EmailService

from .serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = structlog.get_logger(__name__)


class RegisterView(generics.CreateAPIView):
    """Create new customer accounts."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    """Authenticate users via JWT."""

    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    """Refresh JWT access tokens."""

    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """Blacklist refresh tokens on logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Invalidate the provided refresh token."""
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Fetch and update the authenticated profile."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):  # type: ignore[override]
        """Return the current authenticated user."""
        return self.request.user


class PasswordChangeView(APIView):
    """Allow authenticated users to update their password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Persist a new password after validating the old one."""
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada correctamente."})


class PasswordResetView(APIView):
    """Initiate the password reset flow."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Send a reset email when the account exists."""
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.build_reset_payload()
        if payload is not None:
            reset_url = (
                f"{settings.FRONTEND_URL}/auth/reset-password?"
                f"uid={payload['uid']}&token={payload['token']}"
            )
            EmailService.send_transactional(
                to=payload["email"],
                template="password_reset",
                context={
                    "first_name": payload["first_name"],
                    "reset_url": reset_url,
                },
            )
            logger.info("password_reset_requested", email=payload["email"])
        return Response(
            {
                "detail": (
                    "Si el email existe, enviamos instrucciones para restablecer la contraseña."
                )
            }
        )


class PasswordResetConfirmView(APIView):
    """Confirm a password reset token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Update the password when the token is valid."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("password_reset_confirmed", user_id=str(user.id))
        return Response({"detail": "Contraseña restablecida correctamente."})
