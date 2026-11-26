"""Force RLS for all tenant tables.

Revision ID: force_rls_0004
Revises: baseline_0003

The runtime DB role owns the tenant tables, and table owners bypass row level
security unless FORCE is enabled. Without this migration the 101 RLS policies
are decorative for the application's own role.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "force_rls_0004"
down_revision = "baseline_0003"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "accessibility_audits", "affiliate_commissions", "affiliate_programs",
    "affiliates", "app_installations", "app_webhook_subscriptions", "audit_logs",
    "bnpl_providers", "bnpl_transactions", "brands", "cart_items", "carts",
    "categories", "category_translations", "chargebacks", "cms_pages",
    "consent_records", "cookie_consent_settings", "customer_group_members",
    "customer_groups", "customer_subscriptions", "data_subject_requests",
    "digital_assets", "digital_downloads", "draft_order_items", "draft_orders",
    "gift_card_transactions", "gift_cards", "gift_registries", "gift_registry_items",
    "inventory_movements", "invoices", "localized_bundles", "localized_categories",
    "localized_products", "order_items", "orders", "payment_transactions",
    "points_transactions", "product_bundles", "product_images", "product_reviews",
    "products", "refunds", "returns", "seo_metadata", "shipment_items",
    "shipments", "shipping_zones", "store_credit_transactions", "store_credits",
    "subscriber_addresses", "subscribers", "subscription_items", "subscriptions",
    "tax_rates", "transactions", "users", "vouchers", "warehouse_locations",
    "webhook_deliveries", "wishlists",
)


def upgrade() -> None:
    # Apply to every table that actually has row security enabled, so the
    # migration stays correct if the baseline table list changes.
    bind = op.get_bind()
    for (table,) in bind.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    ):
        enabled = bind.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = :t AND relkind = 'r'"
            ),
            {"t": table},
        ).scalar()
        if enabled:
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
