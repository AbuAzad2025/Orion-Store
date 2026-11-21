"""Baseline schema — tenant RLS policies (squashed).

Revision ID: baseline_0003
Revises: baseline_0002
Create Date: 2026-11-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "baseline_0003"
down_revision = "baseline_0002"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "accessibility_audits",
    "affiliate_commissions",
    "affiliate_programs",
    "affiliates",
    "app_installations",
    "app_webhook_subscriptions",
    "audit_logs",
    "bnpl_providers",
    "bnpl_transactions",
    "brands",
    "cart_items",
    "carts",
    "categories",
    "category_translations",
    "chargebacks",
    "cms_pages",
    "consent_records",
    "cookie_consent_settings",
    "customer_group_members",
    "customer_groups",
    "customer_subscriptions",
    "data_subject_requests",
    "digital_assets",
    "digital_downloads",
    "draft_order_items",
    "draft_orders",
    "dropship_orders",
    "dropship_suppliers",
    "feature_flag_overrides",
    "financial_events",
    "financial_reconciliation_runs",
    "fraud_reviews",
    "fraud_rules",
    "fulfillments",
    "gift_registries",
    "import_export_jobs",
    "impersonation_sessions",
    "inventory_levels",
    "inventory_transfers",
    "invoices",
    "license_keys",
    "live_chat_sessions",
    "metafield_definitions",
    "metafields",
    "oauth_applications",
    "order_events",
    "order_items",
    "orders",
    "page_translations",
    "payments",
    "pickup_locations",
    "pickup_slots",
    "platform_commission_ledger",
    "pod_connections",
    "price_lists",
    "product_bundles",
    "product_schema_markup",
    "product_translations",
    "products",
    "quotes",
    "refunds",
    "return_reasons",
    "returns",
    "roles",
    "sandbox_stores",
    "search_boost_rules",
    "search_redirects",
    "search_synonyms",
    "shipping_methods",
    "shipping_rates",
    "shipping_zones",
    "sso_providers",
    "stock_notifications",
    "store_credit_transactions",
    "store_credits",
    "subscription_events",
    "subscription_invoices",
    "subscription_plans",
    "tax_jurisdictions",
    "tax_nexus_rules",
    "tax_rates",
    "tenant_configs",
    "tenant_document_templates",
    "tenant_feature_flag_overrides",
    "tenant_payment_gateways",
    "translation_glossary",
    "users",
    "vouchers",
    "warehouses",
    "workflow_definitions",
    "workflow_runs",
    "affiliate_links",
    "bundle_items",
    "financial_reconciliation_items",
    "fulfillment_items",
    "gift_registry_items",
    "inventory_transfer_items",
    "live_chat_messages",
    "price_list_items",
    "quote_items",
    "return_items",
)

POLICY = "current_setting('app.is_platform_admin', true) = 'true'\n        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint"


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({POLICY}) WITH CHECK ({POLICY})"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
