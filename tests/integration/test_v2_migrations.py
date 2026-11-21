"""Verify v2 migration applies cleanly with correct schema."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


def test_v2_migration(app):
    """Apply all migrations and verify v2 tables + schema."""
    with app.app_context():
        from orion.extensions import db

        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.execute(
            db.text("DROP TABLE IF EXISTS platform_payment_integrations")
        )
        db.session.commit()
        cfg = Config("migrations/alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        command.stamp(cfg, "base")
        command.upgrade(cfg, "head")

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        # Verify a representative set of v2 tables exist
        expected = {
            "subscription_plans",
            "store_credits",
            "draft_orders",
            "tax_jurisdictions",
            "product_bundles",
            "metafield_definitions",
            "pickup_locations",
            "currency_rates",
            "inventory_transfers",
            "import_export_jobs",
            "oauth_applications",
            "fraud_rules",
            "consent_records",
            "workflow_definitions",
            "search_synonyms",
            "affiliate_programs",
            "gift_registries",
            "product_schema_markup",
            "accessibility_audits",
            "live_chat_sessions",
            "tenant_feature_flag_overrides",
        }
        for t in expected:
            assert t in tables, f"Missing v2 table: {t}"
        print(f"All {len(expected)} checked v2 tables exist")

        # Verify FK references are valid
        for t in sorted(tables):
            if t == "alembic_version":
                continue
            for fk in inspector.get_foreign_keys(t):
                assert (
                    fk["referred_table"] in tables
                ), f"Missing referred table {fk['referred_table']} for FK in {t}"
        print("All FK references valid")

        # Verify tenant_feature_flag_overrides has reason + set_by
        tffo_cols = {
            c["name"] for c in inspector.get_columns("tenant_feature_flag_overrides")
        }
        assert "reason" in tffo_cols
        assert "set_by" in tffo_cols
        print("tenant_feature_flag_overrides has reason + set_by columns")
