"""Application configuration."""

from __future__ import annotations

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_dev",
    )
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
