"""Context helpers tests (wave 1)."""

from __future__ import annotations

from flask import g

from core.context import get_tenant, get_tenant_id, get_user, is_platform_admin


def test_context_defaults_outside_request(app):
    with app.app_context():
        assert get_tenant_id() is None
        assert get_tenant() is None
        assert get_user() is None
        assert is_platform_admin() is False


def test_context_reads_flask_g(app):
    with app.test_request_context("/"):
        g.tenant_id = 7
        g.user = None
        assert get_tenant_id() == 7
