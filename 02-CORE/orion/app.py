"""Application factory."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from orion.config import config_by_name
from orion.extensions import db, migrate
from v1.routes import register_blueprints


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()

    app = Flask(__name__)
    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    db.init_app(app)
    migrate.init_app(app, db)

    # Wave 0: register model metadata for Alembic
    import base.base_model  # noqa: F401

    register_blueprints(app)

    @app.get("/health")
    def health() -> tuple[dict, int]:
        return jsonify({"status": "ok", "service": "azadexa-orion"}), 200

    return app
