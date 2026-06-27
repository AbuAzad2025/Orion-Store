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


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = testing_database_uri()
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    PROMETHEUS_ENABLED = False
    CACHE_ENABLED = False
    CELERY_TASK_ALWAYS_EAGER = True


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    # Production MUST use DATABASE_URL — PostgreSQL (managed or self-hosted).


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
