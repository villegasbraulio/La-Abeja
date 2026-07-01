"""Base Django settings for all environments."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
import structlog

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue

        normalized_value = value.strip()
        if (
            len(normalized_value) >= 2
            and normalized_value[0] == normalized_value[-1]
            and normalized_value[0] in {'"', "'"}
        ):
            normalized_value = normalized_value[1:-1]

        os.environ.setdefault(normalized_key, normalized_value)


load_env_file(PROJECT_DIR / ".env")


def get_list_env(name: str, default: str) -> list[str]:
    """Return a normalized list from a comma-separated environment variable."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def get_origin_list_env(name: str, default: str) -> list[str]:
    """Return URL origins from a comma-separated environment variable."""
    return [_normalize_origin(item) for item in get_list_env(name, default)]


def _normalize_origin(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return value.strip().rstrip("/")


def get_first_env(*names: str, default: str = "") -> str:
    """Return the first non-empty environment variable among the provided names."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def get_redis_url(default_db: int) -> str:
    """Build a Redis URL from either a full URL or Render-style host/port vars."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        return redis_url

    redis_host = os.getenv("REDIS_HOST", "").strip()
    if redis_host:
        redis_port = os.getenv("REDIS_PORT", "6379").strip() or "6379"
        return f"redis://{redis_host}:{redis_port}/{default_db}"

    return f"redis://localhost:6379/{default_db}"

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-development-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = get_list_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

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
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media")))

CACHE_URL = os.getenv("CACHE_URL", "").strip()
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
        }
        if CACHE_URL
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "la-abeja-cache",
        }
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "authentication.CustomUser"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

REDIS_URL = get_redis_url(default_db=0)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", get_redis_url(default_db=1))
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
OUTBOX_MAX_ATTEMPTS = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "8"))
OUTBOX_PROCESSING_TIMEOUT_MINUTES = int(
    os.getenv("OUTBOX_PROCESSING_TIMEOUT_MINUTES", "15")
)
OUTBOX_DISPATCH_BATCH_SIZE = int(os.getenv("OUTBOX_DISPATCH_BATCH_SIZE", "100"))
PAYMENT_RECONCILIATION_AGE_MINUTES = int(
    os.getenv("PAYMENT_RECONCILIATION_AGE_MINUTES", "10")
)
BOOKING_HOLD_MINUTES = int(os.getenv("BOOKING_HOLD_MINUTES", "15"))
BOOKING_PAYMENT_RECONCILIATION_AGE_MINUTES = int(
    os.getenv("BOOKING_PAYMENT_RECONCILIATION_AGE_MINUTES", "5")
)
SHIPMENT_RECONCILIATION_AGE_MINUTES = int(
    os.getenv("SHIPMENT_RECONCILIATION_AGE_MINUTES", "10")
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": ("rest_framework.filters.OrderingFilter",),
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

CORS_ALLOWED_ORIGINS = get_origin_list_env(
    "CORS_ALLOWED_ORIGINS",
    f"{FRONTEND_URL},http://127.0.0.1:3000,http://localhost:3000",
)
CSRF_TRUSTED_ORIGINS = get_origin_list_env(
    "CSRF_TRUSTED_ORIGINS",
    f"{FRONTEND_URL},http://127.0.0.1:3000,http://localhost:3000",
)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "reservas@bodegelaabeja.com.ar")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Bodega La Abeja")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY", "")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")
MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED = (
    os.getenv("MERCADOPAGO_WEBHOOK_SIGNATURE_REQUIRED", "True").lower() == "true"
)
MERCADOPAGO_WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = int(
    os.getenv("MERCADOPAGO_WEBHOOK_SIGNATURE_TOLERANCE_SECONDS", "300")
)
MERCADOPAGO_COLLECTOR_ID = os.getenv("MERCADOPAGO_COLLECTOR_ID", "")
ANDREANI_API_KEY = os.getenv("ANDREANI_API_KEY", "")
ANDREANI_API_BASE_URL = os.getenv(
    "ANDREANI_API_BASE_URL",
    "https://apisqa.andreani.com",
)
ANDREANI_ORDER_PATH = os.getenv("ANDREANI_ORDER_PATH", "/v2/ordenes-de-envio")
ANDREANI_MAX_ATTEMPTS = int(os.getenv("ANDREANI_MAX_ATTEMPTS", "3"))
ANDREANI_RETRY_BASE_SECONDS = float(os.getenv("ANDREANI_RETRY_BASE_SECONDS", "0.25"))
ANDREANI_REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("ANDREANI_REQUEST_TIMEOUT_SECONDS", "20")
)
ANDREANI_MASTER_DATA_CACHE_SECONDS = int(
    os.getenv("ANDREANI_MASTER_DATA_CACHE_SECONDS", "86400")
)
ANDREANI_LABEL_ALLOWED_HOSTS = get_list_env(
    "ANDREANI_LABEL_ALLOWED_HOSTS",
    "apis.andreani.com,apisqa.andreani.com,apietiqueta.com",
)
ANDREANI_CONTRACT = os.getenv("ANDREANI_CONTRACT", "")
ANDREANI_CUSTOMER_BRANCH_ID = int(os.getenv("ANDREANI_CUSTOMER_BRANCH_ID", "0"))
ANDREANI_SERVICE_TYPE_STANDARD = os.getenv("ANDREANI_SERVICE_TYPE_STANDARD", "standard")
ANDREANI_SERVICE_TYPE_EXPRESS = os.getenv("ANDREANI_SERVICE_TYPE_EXPRESS", "express")
ANDREANI_COST_CENTER = os.getenv("ANDREANI_COST_CENTER", "ECOMMERCE")
ANDREANI_PRODUCT_TYPE = os.getenv("ANDREANI_PRODUCT_TYPE", "VINOS")
ANDREANI_BILLING_CATEGORY = os.getenv("ANDREANI_BILLING_CATEGORY", "B2C")
ANDREANI_ORIGIN_POSTAL_CODE = os.getenv("ANDREANI_ORIGIN_POSTAL_CODE", "5600")
ANDREANI_ORIGIN_STREET = os.getenv("ANDREANI_ORIGIN_STREET", "Av. Hipolito Yrigoyen")
ANDREANI_ORIGIN_NUMBER = os.getenv("ANDREANI_ORIGIN_NUMBER", "238")
ANDREANI_ORIGIN_FLOOR = os.getenv("ANDREANI_ORIGIN_FLOOR", "")
ANDREANI_ORIGIN_APARTMENT = os.getenv("ANDREANI_ORIGIN_APARTMENT", "")
ANDREANI_ORIGIN_CITY = os.getenv("ANDREANI_ORIGIN_CITY", "San Rafael")
ANDREANI_ORIGIN_REGION = os.getenv("ANDREANI_ORIGIN_REGION", "Mendoza")
ANDREANI_ORIGIN_COUNTRY = os.getenv("ANDREANI_ORIGIN_COUNTRY", "Argentina")
ANDREANI_SENDER_NAME = os.getenv("ANDREANI_SENDER_NAME", DEFAULT_FROM_NAME)
ANDREANI_SENDER_EMAIL = os.getenv("ANDREANI_SENDER_EMAIL", DEFAULT_FROM_EMAIL)
ANDREANI_SENDER_DOCUMENT_TYPE = os.getenv("ANDREANI_SENDER_DOCUMENT_TYPE", "CUIT")
ANDREANI_SENDER_DOCUMENT_NUMBER = os.getenv("ANDREANI_SENDER_DOCUMENT_NUMBER", "")
ANDREANI_SENDER_PHONE = os.getenv("ANDREANI_SENDER_PHONE", "")
ANDREANI_TRACKING_URL_TEMPLATE = os.getenv(
    "ANDREANI_TRACKING_URL_TEMPLATE",
    "https://www.andreani.com/#!/informacionEnvio/{tracking_number}",
)

AI_LLM_PROVIDER = os.getenv("AI_LLM_PROVIDER", "groq").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = get_first_env(
    "GROQ_BASE_URL",
    "GROQ_API_BASE_URL",
    default="https://api.groq.com/openai/v1",
)
DEFAULT_AI_CHAT_MODEL = "openai/gpt-oss-20b" if AI_LLM_PROVIDER == "groq" else "gpt-4.1"
DEFAULT_AI_REASONING_MODEL = (
    "openai/gpt-oss-120b" if AI_LLM_PROVIDER == "groq" else "gpt-5.1"
)
AI_CHAT_MODEL = (
    get_first_env("AI_CHAT_MODEL", "GROQ_MODEL_NAME")
    if AI_LLM_PROVIDER == "groq"
    else get_first_env("AI_CHAT_MODEL")
) or DEFAULT_AI_CHAT_MODEL
AI_REASONING_MODEL = (
    os.getenv("AI_REASONING_MODEL", DEFAULT_AI_REASONING_MODEL) or DEFAULT_AI_REASONING_MODEL
)
AI_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "")
AI_MAX_KNOWLEDGE_RESULTS = int(os.getenv("AI_MAX_KNOWLEDGE_RESULTS", "6"))
AI_USE_LLM = os.getenv("AI_USE_LLM", "True").lower() == "true"
AI_USE_TOOL_CALLING = os.getenv("AI_USE_TOOL_CALLING", "True").lower() == "true"
AI_ENABLE_PGVECTOR = os.getenv("AI_ENABLE_PGVECTOR", "True").lower() == "true"
AI_EMBEDDING_DIMENSIONS = int(os.getenv("AI_EMBEDDING_DIMENSIONS", "1536"))
AI_PGVECTOR_DIMENSIONS = min(AI_EMBEDDING_DIMENSIONS, 1536)
AI_PROVIDER_MAX_RETRIES = int(os.getenv("AI_PROVIDER_MAX_RETRIES", "2"))
AI_PROVIDER_RETRY_BASE_SECONDS = float(os.getenv("AI_PROVIDER_RETRY_BASE_SECONDS", "0.25"))
AI_PROVIDER_MAX_TOOL_ITERATIONS = int(os.getenv("AI_PROVIDER_MAX_TOOL_ITERATIONS", "8"))
AI_INPUT_COST_PER_1M_TOKENS_USD = float(
    os.getenv("AI_INPUT_COST_PER_1M_TOKENS_USD", "0")
)
AI_OUTPUT_COST_PER_1M_TOKENS_USD = float(
    os.getenv("AI_OUTPUT_COST_PER_1M_TOKENS_USD", "0")
)
AI_LOG_CONSOLE_DETAILS = os.getenv("AI_LOG_CONSOLE_DETAILS", "True").lower() == "true"

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
