"""API v1 blueprints — §3.9."""

from __future__ import annotations

from flask import Blueprint, Flask

from v1.accessibility_api import accessibility_bp
from v1.affiliates import affiliates_bp
from v1.app_platform import app_platform_bp
from v1.audit_api import audit_bp
from v1.auth import auth_bp
from v1.b2b import b2b_bp
from v1.bopis import bopis_bp
from v1.bundles import bundles_bp
from v1.categories import categories_bp
from v1.compliance import compliance_bp
from v1.currency_api import currency_bp
from v1.draft_orders import draft_orders_bp
from v1.dropship import dropship_bp
from v1.fraud import fraud_bp
from v1.gift_registries import gift_registries_bp
from v1.i18n import i18n_bp
from v1.impersonation import impersonation_bp
from v1.import_export import import_export_bp
from v1.live_chat import live_chat_bp
from v1.metafields import metafields_bp
from v1.oms import oms_bp
from v1.oms_extensions import oms_ext_bp
from v1.payments import payments_bp
from v1.platform_reconciliation import register_platform_reconciliation_routes
from v1.platform_settings import platform_settings_bp
from v1.platform_stores import register_platform_store_routes
from v1.products import products_bp
from v1.reconciliation_v2 import reconciliation_v2_bp
from v1.returns import returns_bp
from v1.schema_markup import schema_markup_bp
from v1.search_merchandising import search_bp
from v1.shipping import shipping_bp
from v1.stock_notifications import stock_notifications_bp
from v1.store_account import store_account_bp
from v1.store_credit import store_credit_bp
from v1.storefront import storefront_bp
from v1.subscriptions import subscriptions_bp
from v1.tax_api import tax_bp
from v1.tenant_portal import tenant_portal_bp
from v1.tenants import tenant_bp
from v1.users import users_bp
from v1.vouchers import vouchers_bp
from v1.webhooks import webhooks_bp
from v1.workflow_api import workflow_bp

platform_bp = Blueprint("platform", __name__)


@platform_bp.get("/status")
def platform_status():
    return {"blueprint": "platform", "status": "pending"}, 200


API_BLUEPRINTS: list[Blueprint] = [
    auth_bp,
    tenant_bp,
    users_bp,
    products_bp,
    categories_bp,
    payments_bp,
    platform_settings_bp,
    storefront_bp,
    store_account_bp,
    i18n_bp,
    shipping_bp,
    vouchers_bp,
    returns_bp,
    b2b_bp,
    oms_bp,
    tenant_portal_bp,
    platform_bp,
    webhooks_bp,
    subscriptions_bp,
    store_credit_bp,
    draft_orders_bp,
    tax_bp,
    bundles_bp,
    metafields_bp,
    bopis_bp,
    currency_bp,
    import_export_bp,
    stock_notifications_bp,
    fraud_bp,
    compliance_bp,
    workflow_bp,
    search_bp,
    affiliates_bp,
    gift_registries_bp,
    dropship_bp,
    schema_markup_bp,
    accessibility_bp,
    live_chat_bp,
    reconciliation_v2_bp,
    audit_bp,
    app_platform_bp,
    oms_ext_bp,
]


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(tenant_bp, url_prefix="/api/v1/tenants")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    app.register_blueprint(products_bp, url_prefix="/api/v1/products")
    app.register_blueprint(categories_bp, url_prefix="/api/v1/categories")
    app.register_blueprint(payments_bp, url_prefix="/api/v1/payments")
    app.register_blueprint(platform_settings_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(storefront_bp, url_prefix="/api/v1/store")
    app.register_blueprint(store_account_bp, url_prefix="/api/v1/store/account")
    app.register_blueprint(i18n_bp, url_prefix="/api/v1/i18n")
    app.register_blueprint(shipping_bp, url_prefix="/api/v1/shipping")
    app.register_blueprint(vouchers_bp, url_prefix="/api/v1/vouchers")
    app.register_blueprint(returns_bp, url_prefix="/api/v1/returns")
    app.register_blueprint(b2b_bp, url_prefix="/api/v1/b2b")
    app.register_blueprint(oms_bp, url_prefix="/api/v1/oms")
    app.register_blueprint(tenant_portal_bp, url_prefix="/api/v1/tenant")
    register_platform_store_routes(platform_bp)
    register_platform_reconciliation_routes(platform_bp)
    app.register_blueprint(impersonation_bp, url_prefix="/api/v1")
    app.register_blueprint(platform_bp, url_prefix="/api/v1/platform")
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
    # v2 blueprints
    app.register_blueprint(subscriptions_bp, url_prefix="/api/v1/subscriptions")
    app.register_blueprint(store_credit_bp, url_prefix="/api/v1/store-credit")
    app.register_blueprint(draft_orders_bp, url_prefix="/api/v1/draft-orders")
    app.register_blueprint(tax_bp, url_prefix="/api/v1/tax")
    app.register_blueprint(bundles_bp, url_prefix="/api/v1/bundles")
    app.register_blueprint(metafields_bp, url_prefix="/api/v1/metafields")
    app.register_blueprint(bopis_bp, url_prefix="/api/v1/bopis")
    app.register_blueprint(currency_bp, url_prefix="/api/v1/currency")
    app.register_blueprint(import_export_bp, url_prefix="/api/v1/import-export")
    app.register_blueprint(
        stock_notifications_bp, url_prefix="/api/v1/stock-notifications"
    )
    app.register_blueprint(fraud_bp, url_prefix="/api/v1/fraud")
    app.register_blueprint(compliance_bp, url_prefix="/api/v1/compliance")
    app.register_blueprint(workflow_bp, url_prefix="/api/v1/workflow")
    app.register_blueprint(search_bp, url_prefix="/api/v1/search")
    app.register_blueprint(affiliates_bp, url_prefix="/api/v1/affiliates")
    app.register_blueprint(gift_registries_bp, url_prefix="/api/v1/gift-registries")
    app.register_blueprint(dropship_bp, url_prefix="/api/v1/dropship")
    app.register_blueprint(schema_markup_bp, url_prefix="/api/v1/schema-markup")
    app.register_blueprint(accessibility_bp, url_prefix="/api/v1/accessibility")
    app.register_blueprint(live_chat_bp, url_prefix="/api/v1/live-chat")
    app.register_blueprint(reconciliation_v2_bp, url_prefix="/api/v1/reconciliation")
    app.register_blueprint(audit_bp, url_prefix="/api/v1/audit")
    app.register_blueprint(app_platform_bp, url_prefix="/api/v1/app-platform")
    app.register_blueprint(oms_ext_bp, url_prefix="/api/v1/oms-ext")


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
