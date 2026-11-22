"""Application configuration."""

from __future__ import annotations

import os
from datetime import timedelta

# Production + testing target — PostgreSQL only (§0.8, §4.0).
DEFAULT_DEV_DATABASE_URL = "postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_dev"
DEFAULT_TEST_DATABASE_URL = (
    "postgresql://azadexa:azadexa_test@localhost:5433/azadexa_test"
)


def testing_database_uri() -> str:
    """Resolve test DB URI — PostgreSQL by default (production parity).

    Override with ``DATABASE_URL``. Emergency local fallback only:
    ``USE_SQLITE_TESTS=1`` (not supported in CI).
    """
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit
    if os.environ.get("USE_SQLITE_TESTS") == "1":
        return "sqlite:///:memory:"
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_REFRESH_COOKIE_NAME = "refresh_token_cookie"
    JWT_ACCESS_CSRF_COOKIE_NAME = "csrf_access_token"
    JWT_REFRESH_CSRF_COOKIE_NAME = "csrf_refresh_token"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token", "X-CSRF-TOKEN"]
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_DEV_DATABASE_URL)
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "300 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", REDIS_URL)
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "")
    SENTRY_TRACES_SAMPLE_RATE = os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    PROMETHEUS_ENABLED = os.environ.get("PROMETHEUS_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_JSON = os.environ.get("LOG_JSON", "false").lower() in ("1", "true", "yes")
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))
    # Live FX rates from exchangerate-api; testing stays deterministic.
    CURRENCY_LIVE_RATES = os.environ.get("CURRENCY_LIVE_RATES", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    CURRENCY_RATE_TTL_SECONDS = int(os.environ.get("CURRENCY_RATE_TTL_SECONDS", "3600"))
    # Customer-facing FX markup applied when switching display currency.
    CURRENCY_FX_MARKUP_PERCENT = float(
        os.environ.get("CURRENCY_FX_MARKUP_PERCENT", "3")
    )
    CURRENCY_RATE_PROVIDER_URL = os.environ.get(
        "CURRENCY_RATE_PROVIDER_URL", "https://open.er-api.com/v6/latest/{base}"
    )
    BETA_MODE = os.environ.get("BETA_MODE", "false").lower() in ("1", "true", "yes")
    BETA_TENANT_SLUGS = os.environ.get("BETA_TENANT_SLUGS", "")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
    CELERY_TASK_ALWAYS_EAGER = os.environ.get(
        "CELERY_TASK_ALWAYS_EAGER", "false"
    ).lower() in ("1", "true", "yes")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
    WEBHOOK_MAX_AGE_SECONDS = int(os.environ.get("WEBHOOK_MAX_AGE_SECONDS", "300"))
    # Local/CI may use deterministic sandbox stubs; production never may.
    PAYMENT_STUB_ALLOWED = os.environ.get("PAYMENT_STUB_ALLOWED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # Real provider HTTP calls are off by default; production turns them on.
    PAYMENT_LIVE_CALLS_ENABLED = os.environ.get(
        "PAYMENT_LIVE_CALLS_ENABLED", "false"
    ).lower() in ("1", "true", "yes")


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = testing_database_uri()
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    WTF_CSRF_ENABLED = False
    JWT_COOKIE_CSRF_PROTECT = False
    RATELIMIT_ENABLED = False
    PROMETHEUS_ENABLED = False
    CACHE_ENABLED = False
    CURRENCY_LIVE_RATES = False
    CURRENCY_FX_MARKUP_PERCENT = 0
    CELERY_TASK_ALWAYS_EAGER = True


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    # Production MUST use DATABASE_URL — PostgreSQL (managed or self-hosted).
    # Cookies carrying JWTs must never travel over plain HTTP.
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    # HSTS is emitted by core/security_headers.py only when explicitly enabled.
    ENFORCE_HSTS = True
    PAYMENT_STUB_ALLOWED = False
    PAYMENT_LIVE_CALLS_ENABLED = True
    # Structured logs are required for production aggregation/alerting.
    LOG_JSON = True
    SENTRY_ENVIRONMENT = "production"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
