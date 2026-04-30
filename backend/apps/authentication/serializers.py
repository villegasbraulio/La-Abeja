"""Authentication serializers."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serialize the public profile of a user."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "birth_date",
            "avatar",
            "preferred_varietals",
            "newsletter_subscribed",
            "is_staff",
            "full_name",
        ]
        read_only_fields = ["id", "email", "is_staff", "full_name"]


class RegisterSerializer(serializers.ModelSerializer):
    """Create a new user and return tokens."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "birth_date",
            "avatar",
            "preferred_varietals",
            "newsletter_subscribed",
            "password",
        ]

    def create(self, validated_data: dict[str, object]) -> User:
        """Persist a user using the custom manager."""
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user

    def to_representation(self, instance: User) -> dict[str, object]:
        """Append JWT tokens after successful registration."""
        refresh = RefreshToken.for_user(instance)
        return {
            "user": UserSerializer(instance).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login serializer that returns user data."""

    def validate(self, attrs: dict[str, str]) -> dict[str, object]:
        """Attach serialized user data to the token response."""
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    """Validate logout requests carrying a refresh token."""

    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    """Validate password changes for authenticated users."""

    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def validate_old_password(self, value: str) -> str:
        """Ensure the current password matches."""
        request = self.context["request"]
        if not request.user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no coincide.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    """Validate password reset requests."""

    email = serializers.EmailField()

    def build_reset_payload(self) -> dict[str, str] | None:
        """Return token payload if the user exists, otherwise hide enumeration."""
        email = self.validated_data["email"].lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            return None
        return {
            "uid": urlsafe_base64_encode(force_str(user.pk).encode()),
            "token": default_token_generator.make_token(user),
            "email": user.email,
            "first_name": user.first_name,
        }


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validate password reset token confirmation."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def save(self) -> User:
        """Reset the password for the targeted user."""
        try:
            user_id = force_str(urlsafe_base64_decode(self.validated_data["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise serializers.ValidationError({"uid": "Token inválido."}) from exc

        if not default_token_generator.check_token(user, self.validated_data["token"]):
            raise serializers.ValidationError({"token": "Token inválido o vencido."})

        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
