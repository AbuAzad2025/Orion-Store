"""Alembic upgrade/downgrade on PostgreSQL (§0.12.6)."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from orion.extensions import db

pytestmark = pytest.mark.integration


def _alembic_cfg() -> Config:
    cfg = Config("migrations/alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def test_alembic_upgrade_and_downgrade(app):
    with app.app_context():
        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.execute(
            db.text("DROP TABLE IF EXISTS platform_payment_integrations")
        )
        db.session.commit()
        cfg = _alembic_cfg()
        command.stamp(cfg, "base")
        command.upgrade(cfg, "head")
        tables = set(inspect(db.engine).get_table_names())
        assert "tenants" in tables
        assert "users" in tables
        assert "roles" in tables
        assert "products" in tables
        assert "platform_settings" in tables
        assert "carts" in tables
        assert "orders" in tables
        assert "financial_events" in tables
        assert "payments" in tables
        assert "invoices" in tables
        command.downgrade(cfg, "base")
        tables_after = set(inspect(db.engine).get_table_names())
        assert "tenants" not in tables_after


def test_upgrade_is_idempotent(app):
    """Re-running upgrade at head must not change schema or RLS state."""
    with app.app_context():
        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.execute(
            db.text("DROP TABLE IF EXISTS platform_payment_integrations")
        )
        db.session.commit()
        cfg = _alembic_cfg()
        command.stamp(cfg, "base")
        command.upgrade(cfg, "head")

        def snapshot() -> tuple[str, set[str], int]:
            version = db.session.execute(
                db.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            tables = set(inspect(db.engine).get_table_names())
            policies = db.session.execute(
                db.text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
            ).scalar_one()
            return str(version), tables, int(policies)

        before = snapshot()
        command.upgrade(cfg, "head")
        after = snapshot()

        assert after == before
        assert after[0] == "baseline_0003"
