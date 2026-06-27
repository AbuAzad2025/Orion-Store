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
