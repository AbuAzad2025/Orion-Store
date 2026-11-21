"""Every migration must be reversible one step at a time (phase 4, item 1).

For each revision from head to base we downgrade exactly one step and then
re-apply it. The test never modifies migration files; it only reports which
revisions are not reversible.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from orion.extensions import db

pytestmark = pytest.mark.integration


def _config() -> Config:
    cfg = Config("migrations/alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def test_each_migration_downgrade_is_reversible(app):
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

        script = ScriptDirectory.from_config(cfg)
        revisions = [
            revision
            for revision in script.walk_revisions()
            if revision.revision != "base"
        ]
        assert len(revisions) >= 3

        checked: list[str] = []
        for revision in revisions:
            target = revision.down_revision or "base"
            try:
                command.downgrade(cfg, target)
                command.upgrade(cfg, revision.revision)
            except Exception as exc:
                pytest.fail(
                    f"Revision {revision.revision} is not reversible "
                    f"(downgrade -> {target}): {type(exc).__name__}: {exc}"
                )
            checked.append(revision.revision)

        command.upgrade(cfg, "head")
        current = db.session.execute(
            db.text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        assert current == revisions[0].revision
        assert "tenants" in set(inspect(db.engine).get_table_names())
        print(f"Verified reversible revisions: {len(checked)}")
