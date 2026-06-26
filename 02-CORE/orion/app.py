"""Application factory."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from core.exceptions import OrionError
from core.middleware import register_middleware
from orion.config import config_by_name
from orion.extensions import db, jwt, migrate
from v1.routes import register_blueprints


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()

    app = Flask(__name__)
    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    import base.base_model  # noqa: F401
    import catalog.brand  # noqa: F401
    import catalog.category  # noqa: F401
    import catalog.product  # noqa: F401
    import order.cart  # noqa: F401
    import order.order  # noqa: F401
    import platform_models.platform_settings  # noqa: F401
    import tenant.tenant  # noqa: F401
    import tenant.tenant_config  # noqa: F401
    import user.role  # noqa: F401
    import user.user  # noqa: F401

    register_blueprints(app)
    register_middleware(app)

    @app.get("/health")
    def health() -> tuple[dict, int]:
        return jsonify({"status": "ok", "service": "azadexa-orion"}), 200

    @app.errorhandler(OrionError)
    def handle_orion_error(exc: OrionError):
        return jsonify({"error": exc.message}), exc.status_code

    return app
