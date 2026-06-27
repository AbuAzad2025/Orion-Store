"""API v1 blueprints — §3.9."""

from __future__ import annotations

from flask import Blueprint, Flask

from v1.auth import auth_bp
from v1.categories import categories_bp
from v1.payments import payments_bp
from v1.platform_reconciliation import register_platform_reconciliation_routes
from v1.platform_settings import platform_settings_bp
from v1.platform_stores import register_platform_store_routes
from v1.products import products_bp
from v1.shipping import shipping_bp
from v1.storefront import storefront_bp
from v1.tenant_portal import tenant_portal_bp
from v1.tenants import tenant_bp
from v1.vouchers import vouchers_bp
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
    app.register_blueprint(shipping_bp, url_prefix="/api/v1/shipping")
    app.register_blueprint(vouchers_bp, url_prefix="/api/v1/vouchers")
    app.register_blueprint(tenant_portal_bp, url_prefix="/api/v1/tenant")
    register_platform_store_routes(platform_bp)
    register_platform_reconciliation_routes(platform_bp)
    app.register_blueprint(platform_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")


def register_ui_blueprints(app: Flask) -> None:
    from admin_auth import admin_auth_bp

    from admin_assets import admin_assets_bp
    from engine.routes import storefront_ui_bp
    from engine.storefront_assets import storefront_assets_bp
    from platform_admin.routes import platform_admin_bp
    from tenant_admin.routes import tenant_admin_bp

    app.register_blueprint(admin_assets_bp)
    app.register_blueprint(admin_auth_bp, url_prefix="/admin")
    app.register_blueprint(tenant_admin_bp, url_prefix="/admin/store")
    app.register_blueprint(platform_admin_bp, url_prefix="/admin/platform")
    app.register_blueprint(storefront_assets_bp)
    app.register_blueprint(storefront_ui_bp)
