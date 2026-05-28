"""Base Django settings for all environments."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
import structlog

BASE_DIR = Path(__file__).resolve().parents[2]


def get_list_env(name: str, default: str) -> list[str]:
    """Return a normalized list from a comma-separated environment variable."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-development-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = get_list_env("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "apps.authentication",
    "apps.ai",
    "apps.catalog",
    "apps.orders",
    "apps.payments",
    "apps.reservations",
    "apps.automations",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Mendoza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "authentication.CustomUser"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "BLACKLIST_AFTER_ROTATION": True,
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = get_list_env(
    "CORS_ALLOWED_ORIGINS",
    f"{FRONTEND_URL},http://127.0.0.1:3000,http://localhost:3000",
)
CSRF_TRUSTED_ORIGINS = get_list_env(
    "CSRF_TRUSTED_ORIGINS",
    f"{FRONTEND_URL},http://127.0.0.1:3000,http://localhost:3000",
)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "reservas@bodegelaabeja.com.ar")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Bodega La Abeja")

MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY", "")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

ENABLE_WHATSAPP_NOTIFICATIONS = (
    os.getenv("ENABLE_WHATSAPP_NOTIFICATIONS", "False").lower() == "true"
)
ENABLE_SMS_NOTIFICATIONS = os.getenv("ENABLE_SMS_NOTIFICATIONS", "False").lower() == "true"
LOW_STOCK_ALERT_ENABLED = os.getenv("LOW_STOCK_ALERT_ENABLED", "True").lower() == "true"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", "gpt-4.1")
AI_REASONING_MODEL = os.getenv("AI_REASONING_MODEL", "gpt-5.1")
AI_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "text-embedding-3-large")
AI_MAX_KNOWLEDGE_RESULTS = int(os.getenv("AI_MAX_KNOWLEDGE_RESULTS", "6"))
AI_USE_LLM = os.getenv("AI_USE_LLM", "True").lower() == "true"
AI_USE_TOOL_CALLING = os.getenv("AI_USE_TOOL_CALLING", "True").lower() == "true"
AI_ENABLE_PGVECTOR = os.getenv("AI_ENABLE_PGVECTOR", "True").lower() == "true"
AI_EMBEDDING_DIMENSIONS = int(os.getenv("AI_EMBEDDING_DIMENSIONS", "3072"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
