"""Celery tasks must run with an explicit, unprivileged RLS context."""

from __future__ import annotations

import pytest
from core.middleware import bind_task_rls_context
from orion.celery_app import celery_app
from orion.extensions import db

pytestmark = pytest.mark.integration


def test_context_task_defaults_to_unprivileged_context(app):
    @celery_app.task(name="orion.test_default_rls_context")
    def probe_default():
        return (
            db.session.execute(
                db.text("SELECT current_setting('app.tenant_id', true)")
            ).scalar_one(),
            db.session.execute(
                db.text("SELECT current_setting('app.is_platform_admin', true)")
            ).scalar_one(),
        )

    result = probe_default.apply(throw=True).get()
    assert result == ("", "false")


def test_tenant_scoped_task_can_bind_its_own_context(app):
    @celery_app.task(name="orion.test_scoped_rls_context")
    def probe_scoped(tenant_id):
        bind_task_rls_context(tenant_id)
        return db.session.execute(
            db.text("SELECT current_setting('app.tenant_id', true)")
        ).scalar_one()

    assert probe_scoped.apply(args=(4242,), throw=True).get() == "4242"
