"""API rate limiting (§0.5, MVP hardening)."""

from __future__ import annotations

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per hour"],
    enabled=True,
)


def init_rate_limiter(app: Flask) -> None:
    if app.config.get("TESTING"):
        app.config["RATELIMIT_ENABLED"] = False
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    elif not app.config.get("RATELIMIT_STORAGE_URI"):
        app.config["RATELIMIT_STORAGE_URI"] = app.config.get("REDIS_URL", "memory://")
    app.config.setdefault("RATELIMIT_DEFAULT", "300 per hour")
    limiter.init_app(app)
