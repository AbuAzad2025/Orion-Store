"""API v1 blueprints — wave 0 skeleton (§3.9)."""

from __future__ import annotations

from flask import Blueprint, Flask

auth_bp = Blueprint("auth", __name__)
storefront_bp = Blueprint("storefront", __name__)
tenant_bp = Blueprint("tenant", __name__)
platform_bp = Blueprint("platform", __name__)
webhooks_bp = Blueprint("webhooks", __name__)


@auth_bp.get("/status")
def auth_status():
    return {"blueprint": "auth", "status": "pending"}, 200


@storefront_bp.get("/status")
def storefront_status():
    return {"blueprint": "storefront", "status": "pending"}, 200


@tenant_bp.get("/status")
def tenant_status():
    return {"blueprint": "tenant", "status": "pending"}, 200


@platform_bp.get("/status")
def platform_status():
    return {"blueprint": "platform", "status": "pending"}, 200


@webhooks_bp.get("/status")
def webhooks_status():
    return {"blueprint": "webhooks", "status": "pending"}, 200


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(storefront_bp, url_prefix="/api/v1/store")
    app.register_blueprint(tenant_bp, url_prefix="/api/v1/tenant")
    app.register_blueprint(platform_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
