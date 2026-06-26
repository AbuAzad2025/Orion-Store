"""RBAC permission helpers (wave 1)."""

from __future__ import annotations

import pytest
from flask import g

from auth.auth_service import AuthService
from core.exceptions import AuthorizationError
from core.permissions import require_permission, user_has_permission


def test_superuser_has_all_permissions(app):
    admin = AuthService().register_super_admin(
        email="perm-admin@azadexa.com", password="password123"
    )
    with app.test_request_context("/"):
        g.user = admin
        assert user_has_permission("tenant.products.write") is True
        require_permission("tenant.products.write")


def test_tenant_admin_has_tenant_scoped_permissions(app):
    from tenant_svc.tenant_service import TenantService

    tenant = TenantService().create_tenant(
        name="Perm Store", slug="perm-store", email="perm@store.com"
    )
    auth = AuthService()
    user = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@perm.com",
        password="password123",
        is_admin=True,
    )
    with app.test_request_context("/"):
        g.user = user
        assert user_has_permission("tenant.orders.read") is True
        with pytest.raises(AuthorizationError):
            require_permission("platform.settings.write")


def test_anonymous_user_has_no_permissions(app):
    with app.test_request_context("/"):
        assert user_has_permission("tenant.orders.read") is False
