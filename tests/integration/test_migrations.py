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
        cfg = _alembic_cfg()
        command.stamp(cfg, "base")
        command.upgrade(cfg, "head")
        tables = set(inspect(db.engine).get_table_names())
        assert "tenants" in tables
        assert "users" in tables
        assert "roles" in tables
        command.downgrade(cfg, "base")
        tables_after = set(inspect(db.engine).get_table_names())
        assert "tenants" not in tables_after
