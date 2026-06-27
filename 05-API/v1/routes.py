"""API v1 blueprints — §3.9."""

from __future__ import annotations

from flask import Blueprint, Flask

from v1.auth import auth_bp
from v1.categories import categories_bp
from v1.payments import payments_bp
from v1.platform_settings import platform_settings_bp
from v1.products import products_bp
from v1.storefront import storefront_bp
from v1.tenants import tenant_bp
from v1.webhooks import webhooks_bp

platform_bp = Blueprint("platform", __name__)


@platform_bp.get("/status")
def platform_status():
    return {"blueprint": "platform", "status": "pending"}, 200


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(tenant_bp, url_prefix="/api/v1/tenants")
    app.register_blueprint(products_bp, url_prefix="/api/v1/products")
    app.register_blueprint(categories_bp, url_prefix="/api/v1/categories")
    app.register_blueprint(payments_bp, url_prefix="/api/v1/payments")
    app.register_blueprint(platform_settings_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(storefront_bp, url_prefix="/api/v1/store")
    app.register_blueprint(platform_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
