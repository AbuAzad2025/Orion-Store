"""Migrated schema must have valid FKs and tenant indexes."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from orion.extensions import db
from scripts.audit_schema import audit


def _config() -> Config:
    cfg = Config("migrations/alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def test_migrated_schema_passes_audit(app):
    with app.app_context():
        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.execute(
            db.text("DROP TABLE IF EXISTS platform_payment_integrations")
        )
        db.session.commit()

        cfg = _config()
        command.stamp(cfg, "base")
        command.upgrade(cfg, "head")

        issues = audit(inspect(db.engine))
        assert issues == [], "\n".join(issues)
