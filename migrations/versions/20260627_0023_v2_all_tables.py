"""v2 — all post-MVP tables: subs, credit, drafts, tax, bundles, bopis, transfers, app platform, fraud, compliance, workflow, search, affiliates, gifts, dropship, schema, accessibility, chat, reconciliation, audit

Revision ID: v2_all_001
Revises: wave15_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "v2_all_001"
down_revision = "wave15_001"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def _tenant_rls(table: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
        )
        """
    )


def _no_rls(_table: str) -> None:
    pass


def upgrade() -> None:
    # ── Feature flag rollout % ──
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("feature_flags")]
    if "rollout_percent" not in columns:
        op.add_column(
            "feature_flags",
            sa.Column("rollout_percent", sa.Integer(), server_default=sa.text("100"), nullable=False),
        )

    # ── Tenant feature flag overrides ──
    op.create_table(
        "tenant_feature_flag_overrides",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("flag_id", _PK, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("set_by", _PK, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flag_id"], ["feature_flags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_feature_flag_overrides_tenant_id", "tenant_feature_flag_overrides", ["tenant_id"])

    # ── Subscription plans ──
    op.create_table(
        "subscription_plans",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("billing_period_days", sa.Integer(), nullable=False),
        sa.Column("trial_period_days", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("max_orders_per_cycle", sa.Integer(), nullable=True),
        sa.Column("max_products", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_sub_plans_code"),
    )
    op.create_index("ix_subscription_plans_tenant_id", "subscription_plans", ["tenant_id"])
    _tenant_rls("subscription_plans")

    # ── Customer subscriptions ──
    op.create_table(
        "customer_subscriptions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("plan_id", _PK, nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_period_start", _TS, server_default=_NOW, nullable=False),
        sa.Column("current_period_end", _TS, nullable=False),
        sa.Column("trial_end", _TS, nullable=True),
        sa.Column("cancelled_at", _TS, nullable=True),
        sa.Column("pause_resume_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "customer_email", name="uq_cust_sub_email"),
    )
    op.create_index("ix_customer_subscriptions_tenant_id", "customer_subscriptions", ["tenant_id"])
    op.create_index("ix_customer_subscriptions_plan_id", "customer_subscriptions", ["plan_id"])
    _tenant_rls("customer_subscriptions")

    # ── Subscription invoices ──
    op.create_table(
        "subscription_invoices",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("subscription_id", _PK, nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("due_date", _TS, nullable=False),
        sa.Column("paid_at", _TS, nullable=True),
        sa.Column("payment_id", _PK, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["customer_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index("ix_subscription_invoices_tenant_id", "subscription_invoices", ["tenant_id"])
    op.create_index("ix_subscription_invoices_subscription_id", "subscription_invoices", ["subscription_id"])
    _tenant_rls("subscription_invoices")

    # ── Subscription events ──
    op.create_table(
        "subscription_events",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("subscription_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["customer_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_events_subscription_id", "subscription_events", ["subscription_id"])
    op.create_index("ix_subscription_events_tenant_id", "subscription_events", ["tenant_id"])

    # ── Digital assets ──
    op.create_table(
        "digital_assets",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("max_downloads", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_digital_assets_tenant_id", "digital_assets", ["tenant_id"])
    op.create_index("ix_digital_assets_product_id", "digital_assets", ["product_id"])
    _tenant_rls("digital_assets")

    # ── Digital downloads ──
    op.create_table(
        "digital_downloads",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("asset_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("download_token", sa.String(255), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", _TS, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["digital_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("download_token"),
    )
    op.create_index("ix_digital_downloads_tenant_id", "digital_downloads", ["tenant_id"])
    op.create_index("ix_digital_downloads_asset_id", "digital_downloads", ["asset_id"])
    op.create_index("ix_digital_downloads_order_id", "digital_downloads", ["order_id"])

    # ── License keys ──
    op.create_table(
        "license_keys",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("order_item_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("activated_at", _TS, nullable=True),
        sa.Column("expires_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_license_keys_tenant_id", "license_keys", ["tenant_id"])
    op.create_index("ix_license_keys_order_item_id", "license_keys", ["order_item_id"])

    # ── Store credits ──
    op.create_table(
        "store_credits",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "customer_email", name="uq_store_credit_email"),
    )
    op.create_index("ix_store_credits_tenant_id", "store_credits", ["tenant_id"])
    op.create_index("ix_store_credits_customer_email", "store_credits", ["customer_email"])
    _tenant_rls("store_credits")

    op.create_table(
        "store_credit_transactions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("credit_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", _PK, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["credit_id"], ["store_credits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_credit_transactions_credit_id", "store_credit_transactions", ["credit_id"])
    op.create_index("ix_store_credit_transactions_tenant_id", "store_credit_transactions", ["tenant_id"])

    # ── Draft orders ──
    op.create_table(
        "draft_orders",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("draft_number", sa.String(50), nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_first_name", sa.String(100), nullable=True),
        sa.Column("customer_last_name", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("shipping_address", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("send_email_invite", sa.Boolean(), nullable=False),
        sa.Column("converted_order_id", _PK, nullable=True),
        sa.Column("completed_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_number"),
    )
    op.create_index("ix_draft_orders_tenant_id", "draft_orders", ["tenant_id"])
    _tenant_rls("draft_orders")

    op.create_table(
        "draft_order_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("draft_order_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=True),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["draft_order_id"], ["draft_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_draft_order_items_draft_order_id", "draft_order_items", ["draft_order_id"])
    op.create_index("ix_draft_order_items_tenant_id", "draft_order_items", ["tenant_id"])

    # ── Tax ──
    op.create_table(
        "tax_jurisdictions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_tax_jurisdictions"),
    )
    op.create_index("ix_tax_jurisdictions_tenant_id", "tax_jurisdictions", ["tenant_id"])
    _tenant_rls("tax_jurisdictions")

    op.create_table(
        "tax_rates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("jurisdiction_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("product_tax_code", sa.String(50), nullable=True),
        sa.Column("is_compound", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["tax_jurisdictions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jurisdiction_id", "product_tax_code", name="uq_tax_rates"),
    )
    op.create_index("ix_tax_rates_jurisdiction_id", "tax_rates", ["jurisdiction_id"])
    op.create_index("ix_tax_rates_tenant_id", "tax_rates", ["tenant_id"])

    op.create_table(
        "tax_nexus_rules",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("jurisdiction_id", _PK, nullable=False),
        sa.Column("nexus_type", sa.String(20), nullable=False),
        sa.Column("threshold_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("threshold_transactions", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["tax_jurisdictions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_nexus_rules_tenant_id", "tax_nexus_rules", ["tenant_id"])

    # ── Bundles ──
    op.create_table(
        "product_bundles",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bundle_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("max_per_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_bundles_tenant_id", "product_bundles", ["tenant_id"])
    _tenant_rls("product_bundles")

    op.create_table(
        "bundle_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("bundle_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["product_bundles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bundle_items_bundle_id", "bundle_items", ["bundle_id"])

    # ── Metafields ──
    op.create_table(
        "metafield_definitions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("owner_type", sa.String(50), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("field_type", sa.String(50), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("validation_rules", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "owner_type", "key", name="uq_metafield_def"),
    )
    op.create_index("ix_metafield_definitions_tenant_id", "metafield_definitions", ["tenant_id"])
    _tenant_rls("metafield_definitions")

    op.create_table(
        "metafields",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("definition_id", _PK, nullable=False),
        sa.Column("owner_id", _PK, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("json_value", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["definition_id"], ["metafield_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("definition_id", "owner_id", name="uq_metafield_value"),
    )
    op.create_index("ix_metafields_tenant_id", "metafields", ["tenant_id"])
    op.create_index("ix_metafields_definition_id", "metafields", ["definition_id"])
    op.create_index("ix_metafields_owner_id", "metafields", ["owner_id"])

    # ── BOPIS ──
    op.create_table(
        "pickup_locations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("warehouse_id", _PK, nullable=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.JSON(), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_pickup_locations"),
    )
    op.create_index("ix_pickup_locations_tenant_id", "pickup_locations", ["tenant_id"])
    _tenant_rls("pickup_locations")

    op.create_table(
        "pickup_slots",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("location_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False),
        sa.Column("max_orders", sa.Integer(), nullable=False),
        sa.Column("current_orders", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["pickup_locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pickup_slots_location_id", "pickup_slots", ["location_id"])
    op.create_index("ix_pickup_slots_tenant_id", "pickup_slots", ["tenant_id"])

    # ── Currency rates ──
    op.execute("DROP TABLE IF EXISTS currency_rates")
    op.create_table(
        "currency_rates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("from_currency", sa.String(3), nullable=False),
        sa.Column("to_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("rate_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_currency", "to_currency", "rate_date", name="uq_currency_rates"),
    )

    # ── Inventory transfers ──
    op.create_table(
        "inventory_transfers",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("transfer_number", sa.String(50), nullable=False),
        sa.Column("from_warehouse_id", _PK, nullable=False),
        sa.Column("to_warehouse_id", _PK, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transfer_number"),
    )
    op.create_index("ix_inventory_transfers_tenant_id", "inventory_transfers", ["tenant_id"])

    op.create_table(
        "inventory_transfer_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("transfer_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["transfer_id"], ["inventory_transfers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transfer_items_transfer_id", "inventory_transfer_items", ["transfer_id"])

    # ── Import / export ──
    op.create_table(
        "import_export_jobs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_export_jobs_tenant_id", "import_export_jobs", ["tenant_id"])

    # ── Stock notifications ──
    op.create_table(
        "stock_notifications",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("is_notified", sa.Boolean(), nullable=False),
        sa.Column("notified_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_notifications_tenant_id", "stock_notifications", ["tenant_id"])
    op.create_index("ix_stock_notifications_product_id", "stock_notifications", ["product_id"])

    # ── App platform ──
    op.create_table(
        "oauth_applications",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("ix_oauth_applications_tenant_id", "oauth_applications", ["tenant_id"])

    op.create_table(
        "app_installations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("app_id", _PK, nullable=False),
        sa.Column("installed_by", _PK, nullable=False),
        sa.Column("access_token_hash", sa.String(255), nullable=True),
        sa.Column("refresh_token_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], ["oauth_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["installed_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_installations_tenant_id", "app_installations", ["tenant_id"])

    op.create_table(
        "app_webhook_subscriptions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("installation_id", _PK, nullable=False),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("callback_url", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["installation_id"], ["app_installations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_webhook_subscriptions_tenant_id", "app_webhook_subscriptions", ["tenant_id"])

    op.create_table(
        "sandbox_stores",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_sandbox_stores_tenant_id", "sandbox_stores", ["tenant_id"])

    # ── Fraud ──
    op.create_table(
        "fraud_rules",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("operator", sa.String(20), nullable=False),
        sa.Column("threshold_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fraud_rules_tenant_id", "fraud_rules", ["tenant_id"])

    op.create_table(
        "fraud_reviews",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reviewed_by", _PK, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fraud_reviews_tenant_id", "fraud_reviews", ["tenant_id"])
    op.create_index("ix_fraud_reviews_order_id", "fraud_reviews", ["order_id"])

    op.create_table(
        "chargebacks",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("payment_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason_code", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_due_date", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chargebacks_tenant_id", "chargebacks", ["tenant_id"])
    op.create_index("ix_chargebacks_payment_id", "chargebacks", ["payment_id"])

    # ── Compliance ──
    op.create_table(
        "consent_records",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consent_records_tenant_id", "consent_records", ["tenant_id"])
    op.create_index("ix_consent_records_customer_email", "consent_records", ["customer_email"])

    op.create_table(
        "data_subject_requests",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_subject_requests_tenant_id", "data_subject_requests", ["tenant_id"])

    op.create_table(
        "cookie_consent_settings",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("necessary_cookies", sa.JSON(), nullable=False),
        sa.Column("analytics_cookies", sa.JSON(), nullable=False),
        sa.Column("marketing_cookies", sa.JSON(), nullable=False),
        sa.Column("banner_message", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cookie_consent_settings_tenant_id", "cookie_consent_settings", ["tenant_id"])

    op.create_table(
        "sso_providers",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("issuer_url", sa.String(1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("auto_provision", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sso_providers_tenant_id", "sso_providers", ["tenant_id"])

    # ── Workflow ──
    op.create_table(
        "workflow_definitions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger_event", sa.String(100), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_definitions_tenant_id", "workflow_definitions", ["tenant_id"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("definition_id", _PK, nullable=False),
        sa.Column("trigger_event_id", _PK, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["definition_id"], ["workflow_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_tenant_id", "workflow_runs", ["tenant_id"])
    op.create_index("ix_workflow_runs_definition_id", "workflow_runs", ["definition_id"])

    # ── Search merchandising ──
    op.create_table(
        "search_synonyms",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("term", sa.String(255), nullable=False),
        sa.Column("synonyms", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_synonyms_tenant_id", "search_synonyms", ["tenant_id"])

    op.create_table(
        "search_redirects",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("query_term", sa.String(255), nullable=False),
        sa.Column("redirect_url", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_redirects_tenant_id", "search_redirects", ["tenant_id"])

    op.create_table(
        "search_boost_rules",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=True),
        sa.Column("category_id", _PK, nullable=True),
        sa.Column("boost_factor", sa.Integer(), nullable=False),
        sa.Column("query_keyword", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_boost_rules_tenant_id", "search_boost_rules", ["tenant_id"])

    # ── Affiliates ──
    op.create_table(
        "affiliate_programs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("commission_type", sa.String(20), nullable=False),
        sa.Column("commission_value", sa.Numeric(5, 2), nullable=False),
        sa.Column("cookie_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_aff_programs"),
    )
    op.create_index("ix_affiliate_programs_tenant_id", "affiliate_programs", ["tenant_id"])

    op.create_table(
        "affiliates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("program_id", _PK, nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("referral_code", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("total_earned", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_paid", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["affiliate_programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_code"),
    )
    op.create_index("ix_affiliates_tenant_id", "affiliates", ["tenant_id"])

    op.create_table(
        "affiliate_commissions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("affiliate_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("paid_at", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["affiliate_id"], ["affiliates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_affiliate_commissions_tenant_id", "affiliate_commissions", ["tenant_id"])
    op.create_index("ix_affiliate_commissions_affiliate_id", "affiliate_commissions", ["affiliate_id"])

    op.create_table(
        "affiliate_links",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("affiliate_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["affiliate_id"], ["affiliates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_affiliate_links_affiliate_id", "affiliate_links", ["affiliate_id"])

    # ── Gift registries ──
    op.create_table(
        "gift_registries",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("registry_name", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("event_date", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_gift_registries_tenant_id", "gift_registries", ["tenant_id"])

    op.create_table(
        "gift_registry_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("registry_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("purchased_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["registry_id"], ["gift_registries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gift_registry_items_registry_id", "gift_registry_items", ["registry_id"])

    # ── Dropship ──
    op.create_table(
        "pod_connections",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("api_url", sa.String(1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pod_connections_tenant_id", "pod_connections", ["tenant_id"])

    op.create_table(
        "dropship_suppliers",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("fulfillment_time_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dropship_suppliers_tenant_id", "dropship_suppliers", ["tenant_id"])

    op.create_table(
        "dropship_orders",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("supplier_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("supplier_order_ref", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["dropship_suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dropship_orders_tenant_id", "dropship_orders", ["tenant_id"])
    op.create_index("ix_dropship_orders_supplier_id", "dropship_orders", ["supplier_id"])
    op.create_index("ix_dropship_orders_order_id", "dropship_orders", ["order_id"])

    # ── Schema markup ──
    op.create_table(
        "product_schema_markup",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("schema_type", sa.String(50), nullable=False),
        sa.Column("json_ld", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )
    op.create_index("ix_product_schema_markup_tenant_id", "product_schema_markup", ["tenant_id"])
    op.create_index("ix_product_schema_markup_product_id", "product_schema_markup", ["product_id"])

    # ── Accessibility ──
    op.create_table(
        "accessibility_audits",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("page_url", sa.String(1024), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accessibility_audits_tenant_id", "accessibility_audits", ["tenant_id"])

    # ── Live chat ──
    op.create_table(
        "live_chat_sessions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("session_token", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("assigned_to", _PK, nullable=True),
        sa.Column("ended_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index("ix_live_chat_sessions_tenant_id", "live_chat_sessions", ["tenant_id"])

    op.create_table(
        "live_chat_messages",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("session_id", _PK, nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["live_chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_live_chat_messages_session_id", "live_chat_messages", ["session_id"])

    # ── Financial reconciliation (v2) ──
    op.create_table(
        "financial_reconciliation_runs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("run_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_events", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("discrepancy_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_number"),
    )
    op.create_index("ix_financial_reconciliation_runs_tenant_id", "financial_reconciliation_runs", ["tenant_id"])

    op.create_table(
        "financial_reconciliation_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("run_id", _PK, nullable=False),
        sa.Column("financial_event_id", _PK, nullable=False),
        sa.Column("expected_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("actual_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["financial_reconciliation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["financial_event_id"], ["financial_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_reconciliation_items_run_id", "financial_reconciliation_items", ["run_id"])

    # ── Platform audit ──
    op.create_table(
        "platform_audit_reports",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("report_number", sa.String(50), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("generated_by", _PK, nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_number"),
    )

    op.create_table(
        "platform_admin_audit_log",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("user_id", _PK, nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", _PK, nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_admin_audit_log_user_id", "platform_admin_audit_log", ["user_id"])

    # ── Apply RLS to all tenant-scoped v2 tables atomically ──
    _rls_all_tables = [
        "tenant_feature_flag_overrides",
        "subscription_plans", "customer_subscriptions", "subscription_invoices",
        "subscription_events", "digital_assets", "digital_downloads", "license_keys",
        "store_credits", "store_credit_transactions",
        "draft_orders", "draft_order_items",
        "tax_jurisdictions", "tax_rates", "tax_nexus_rules",
        "product_bundles", "metafield_definitions", "metafields",
        "pickup_locations", "pickup_slots",
        "inventory_transfers", "import_export_jobs", "stock_notifications",
        "oauth_applications", "app_installations", "app_webhook_subscriptions", "sandbox_stores",
        "fraud_rules", "fraud_reviews", "chargebacks",
        "consent_records", "data_subject_requests", "cookie_consent_settings", "sso_providers",
        "workflow_definitions", "workflow_runs",
        "search_synonyms", "search_redirects", "search_boost_rules",
        "affiliate_programs", "affiliates", "affiliate_commissions",
        "gift_registries", "pod_connections", "dropship_suppliers", "dropship_orders",
        "product_schema_markup", "accessibility_audits",
        "live_chat_sessions", "financial_reconciliation_runs",
    ]
    for t in _rls_all_tables:
        _tenant_rls(t)


def downgrade() -> None:
    tables = [
        "platform_admin_audit_log", "platform_audit_reports",
        "financial_reconciliation_items", "financial_reconciliation_runs",
        "live_chat_messages", "live_chat_sessions",
        "accessibility_audits", "product_schema_markup",
        "dropship_orders", "dropship_suppliers", "pod_connections",
        "gift_registry_items", "gift_registries",
        "affiliate_links", "affiliate_commissions", "affiliates", "affiliate_programs",
        "search_boost_rules", "search_redirects", "search_synonyms",
        "workflow_runs", "workflow_definitions",
        "sso_providers", "cookie_consent_settings", "data_subject_requests", "consent_records",
        "chargebacks", "fraud_reviews", "fraud_rules",
        "sandbox_stores", "app_webhook_subscriptions", "app_installations", "oauth_applications",
        "stock_notifications", "import_export_jobs",
        "inventory_transfer_items", "inventory_transfers",
        "currency_rates",
        "pickup_slots", "pickup_locations",
        "metafields", "metafield_definitions",
        "bundle_items", "product_bundles",
        "tax_nexus_rules", "tax_rates", "tax_jurisdictions",
        "draft_order_items", "draft_orders",
        "store_credit_transactions", "store_credits",
        "license_keys", "digital_downloads", "digital_assets",
        "subscription_events", "subscription_invoices", "customer_subscriptions", "subscription_plans",
        "tenant_feature_flag_overrides",
    ]
    rls_tables = [
        "tenant_feature_flag_overrides",
        "subscription_plans", "customer_subscriptions", "subscription_invoices",
        "subscription_events", "digital_assets", "digital_downloads", "license_keys",
        "store_credits", "store_credit_transactions",
        "draft_orders", "draft_order_items",
        "tax_jurisdictions", "tax_rates", "tax_nexus_rules",
        "product_bundles", "metafield_definitions", "metafields",
        "pickup_locations", "pickup_slots",
        "inventory_transfers", "import_export_jobs", "stock_notifications",
        "oauth_applications", "app_installations", "app_webhook_subscriptions", "sandbox_stores",
        "fraud_rules", "fraud_reviews", "chargebacks",
        "consent_records", "data_subject_requests", "cookie_consent_settings", "sso_providers",
        "workflow_definitions", "workflow_runs",
        "search_synonyms", "search_redirects", "search_boost_rules",
        "affiliate_programs", "affiliates", "affiliate_commissions",
        "gift_registries", "pod_connections", "dropship_suppliers", "dropship_orders",
        "product_schema_markup", "accessibility_audits",
        "live_chat_sessions", "financial_reconciliation_runs",
    ]
    if op.get_bind().dialect.name == "postgresql":
        for t in rls_tables:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
            op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
    for t in tables:
        op.drop_table(t)

    # Recreate old currency_rates table for wave2_004 downgrade compatibility
    op.create_table(
        "currency_rates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency", "target_currency", name="uq_currency_rates_pair"
        ),
    )

    conn = op.get_bind()
    column_names = [row[1] for row in conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='feature_flags' AND column_name='rollout_percent'")).fetchall()]
    if "rollout_percent" in column_names:
        op.drop_column("feature_flags", "rollout_percent")
