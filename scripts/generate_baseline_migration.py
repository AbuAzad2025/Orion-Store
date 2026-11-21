#!/usr/bin/env python3
"""Generate clean chained baseline migrations from SQLAlchemy metadata.

Pre-launch project: the old 25-migration chain is squashed into three
reproducible steps (tables, indexes, RLS), each under the 200-line limit.

Usage:
    python scripts/generate_baseline_migration.py --output-dir migrations/versions
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for part in (
    "02-CORE",
    "03-MODELS",
    "04-SERVICES",
    "05-API",
    "06-STOREFRONT",
    "07-ADMIN",
):
    path = str(ROOT / part)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENCRYPTION_KEY", "baseline-generator-key")
os.environ.setdefault("USE_SQLITE_TESTS", "1")

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from orion.app import create_app

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
    # Child tables now carry tenant_id so RLS can isolate them directly.
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

LEGACY_TABLE_SQL = """CREATE TABLE platform_payment_integrations (
    id BIGSERIAL NOT NULL,
    provider VARCHAR(30) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN NOT NULL,
    config JSON NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (provider)
)"""

PLATFORM_SETTINGS_SEED_SQL = """INSERT INTO platform_settings (
    platform_name, footer_html, owner_name, owner_phone, owner_phone_intl,
    support_email, default_currency, default_language,
    default_commission_percent, singleton, valuepayment_enabled, valuepayment_config
) VALUES (
    'Azadexa',
    '<footer id="azadexa-platform-footer" class="azadexa-platform-footer" data-immutable="true">Powered by Azadexa &mdash; Ahmad Ghannam</footer>',
    'Ahmad Ghannam', '0562150193', '+972562150193',
    'support@azadexa.com', 'ILS', 'ar', 0.0100, '1', true, '{}'::json
) ON CONFLICT (singleton) DO NOTHING"""

POLICY = """current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint"""

# Indexes/constraints created by the old chain but absent from the models.
# Preserved so the baseline does not lose performance or uniqueness guarantees.
EXTRA_INDEXES = (
    "CREATE INDEX ix_categories_tenant_active ON categories USING btree (tenant_id, sort_order, name) WHERE (deleted_at IS NULL)",
    "CREATE INDEX ix_category_translations_tenant_locale ON category_translations USING btree (tenant_id, locale)",
    "CREATE INDEX ix_feature_flags_category ON feature_flags USING btree (category)",
    "CREATE INDEX ix_platform_admin_audit_log_user_id ON platform_admin_audit_log USING btree (user_id)",
    "CREATE INDEX ix_product_translations_tenant_locale ON product_translations USING btree (tenant_id, locale)",
    "CREATE INDEX ix_products_tenant_published_active ON products USING btree (tenant_id, created_at DESC) WHERE ((deleted_at IS NULL) AND (is_published = true))",
    "CREATE INDEX ix_tenant_gateways_tenant ON tenant_payment_gateways USING btree (tenant_id)",
    "CREATE UNIQUE INDEX product_schema_markup_product_id_key ON product_schema_markup USING btree (product_id)",
    # One active/successful payment per order; failed attempts may be retried.
    "CREATE UNIQUE INDEX uq_payments_order_active ON payments USING btree (order_id) WHERE (status IN ('pending', 'processing', 'completed', 'refunded'))",
)


def _header(doc: str, revision: str, down: str | None) -> list[str]:
    down_repr = "None" if down is None else repr(down)
    return [
        f'"""{doc}',
        "",
        f"Revision ID: {revision}",
        f"Revises: {down or 'None'}",
        "Create Date: 2026-11-19",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from alembic import op",
        "from sqlalchemy import inspect",
        "",
        f"revision = {revision!r}",
        f"down_revision = {down_repr}",
        "branch_labels = None",
        "depends_on = None",
        "",
        "",
    ]


def _pg_guard() -> list[str]:
    return [
        "    if op.get_bind().dialect.name != 'postgresql':",
        "        return",
    ]


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path} ({len(lines)} lines)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("migrations/versions"))
    args = parser.parse_args()

    app = create_app("testing")
    dialect = postgresql.dialect()
    with app.app_context():
        from orion.extensions import db

        tables = db.metadata.sorted_tables
        output = args.output_dir

        # 0001 — tables
        lines = _header(
            "Baseline schema — all tables (squashed).", "baseline_0001", None
        )
        lines += ["def upgrade() -> None:"]
        lines += _pg_guard()
        for table in tables:
            ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
            lines.append(f"    op.execute({ddl!r})")
        lines.append(f"    op.execute({LEGACY_TABLE_SQL!r})")
        lines.append(f"    op.execute({PLATFORM_SETTINGS_SEED_SQL!r})")
        lines += [
            "",
            "",
            "def downgrade() -> None:",
        ]
        lines += _pg_guard()
        lines += [
            "    op.execute('DROP TABLE IF EXISTS platform_payment_integrations')",
            "    bind = op.get_bind()",
            "    for table in reversed(inspect(bind).get_table_names()):",
            "        if table != 'alembic_version':",
            "            op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')",
        ]
        _write(output / "20261119_0001_baseline_tables.py", lines)

        # 0002 — indexes
        lines = _header(
            "Baseline schema — indexes (squashed).", "baseline_0002", "baseline_0001"
        )
        lines += ["def upgrade() -> None:"]
        lines += _pg_guard()
        for table in tables:
            for index in sorted(table.indexes, key=lambda idx: idx.name or ""):
                ddl = str(CreateIndex(index).compile(dialect=dialect)).strip()
                lines.append(f"    op.execute({ddl!r})")
        lines.append("")
        for ddl in EXTRA_INDEXES:
            lines.append(f"    op.execute({ddl!r})")
        lines += [
            "",
            "",
            "def downgrade() -> None:",
        ]
        lines += _pg_guard()
        lines += [
            "    bind = op.get_bind()",
            "    inspector = inspect(bind)",
            "    for table in inspector.get_table_names():",
            "        if table == 'alembic_version':",
            "            continue",
            "        for index in inspector.get_indexes(table):",
            "            name = index.get('name')",
            "            if not name:",
            "                continue",
            "            # Constraint-backed unique indexes must be dropped via",
            "            # the constraint; standalone indexes via DROP INDEX.",
            "            op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}')",
            "            op.execute(f'DROP INDEX IF EXISTS {name}')",
        ]
        _write(output / "20261119_0002_baseline_indexes.py", lines)

        # 0003 — RLS
        lines = _header(
            "Baseline schema — tenant RLS policies (squashed).",
            "baseline_0003",
            "baseline_0002",
        )
        lines += [
            "TENANT_TABLES = (",
            *[f'    "{table}",' for table in TENANT_TABLES],
            ")",
            "",
            f"POLICY = {POLICY!r}",
            "",
            "",
            "def upgrade() -> None:",
        ]
        lines += _pg_guard()
        lines += [
            "    for table in TENANT_TABLES:",
            "        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')",
            "        op.execute(",
            '            f"CREATE POLICY tenant_isolation ON {table} "',
            '            f"USING ({POLICY}) WITH CHECK ({POLICY})"',
            "        )",
            "",
            "",
            "def downgrade() -> None:",
        ]
        lines += _pg_guard()
        lines += [
            "    for table in TENANT_TABLES:",
            "        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON {table}')",
        ]
        _write(output / "20261119_0003_baseline_rls.py", lines)


if __name__ == "__main__":
    main()
