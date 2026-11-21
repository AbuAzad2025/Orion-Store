"""Detailed RBAC — user_roles → role_permissions → permissions (§3.5)."""

from __future__ import annotations

import pytest
from flask import g

from auth.auth_service import AuthService
from core.exceptions import AuthorizationError, NotFoundError
from core.permissions import require_permission, user_has_permission
from orion.extensions import db
from tenant_svc.tenant_service import TenantService
from user.role import Permission, Role, RolePermission, UserRole


def _tenant(name: str, slug: str, email: str):
    return TenantService().create_tenant(name=name, slug=slug, email=email)


def _seed_role(tenant_id: int, role_code: str, permission_code: str) -> Role:
    role = Role(tenant_id=tenant_id, name=role_code, code=role_code)
    permission = Permission(
        code=permission_code,
        name=permission_code,
        category="store",
        is_system=False,
    )
    db.session.add_all([role, permission])
    db.session.commit()
    db.session.add(
        RolePermission(role_id=role.id, permission_id=permission.id)
    )
    db.session.commit()
    return role


def test_granted_role_permission_allows_access(app):
    tenant = _tenant("RBAC Store", "rbac-store", "rbac@store.com")
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="customer@rbac.com",
        password="password123",
        is_admin=False,
    )

    with app.test_request_context("/"):
        g.user = customer
        assert user_has_permission("store.orders.read") is False
        with pytest.raises(AuthorizationError):
            require_permission("store.orders.read")

    role = _seed_role(tenant.id, "store_staff", "store.orders.read")
    assignment = AuthService().assign_role(
        tenant_id=tenant.id, user_id=customer.id, role_code="store_staff"
    )
    assert assignment.user_id == customer.id
    assert assignment.role_id == role.id

    with app.test_request_context("/"):
        g.user = customer
        assert user_has_permission("store.orders.read") is True
        require_permission("store.orders.read")


def test_default_tenant_admin_keeps_tenant_permissions(app):
    tenant = _tenant("Admin Store", "admin-store", "admin@store.com")
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="boss@rbac.com",
        password="password123",
        is_admin=True,
    )

    with app.test_request_context("/"):
        g.user = admin
        assert user_has_permission("tenant.orders.read") is True
        assert user_has_permission("tenant.products.write") is True
        require_permission("tenant.orders.read")
        with pytest.raises(AuthorizationError):
            require_permission("platform.settings.write")


def test_cross_tenant_role_grant_is_ignored_and_rejected(app):
    tenant_a = _tenant("Tenant A", "rbac-tenant-a", "a@rbac.com")
    tenant_b = _tenant("Tenant B", "rbac-tenant-b", "b@rbac.com")
    role_a = _seed_role(tenant_a.id, "store_staff", "store.orders.read")
    user_a = AuthService().register_tenant_user(
        tenant_id=tenant_a.id,
        email="user-a@rbac.com",
        password="password123",
        is_admin=False,
    )
    user_b = AuthService().register_tenant_user(
        tenant_id=tenant_b.id,
        email="user-b@rbac.com",
        password="password123",
        is_admin=False,
    )

    # A stray cross-tenant user_roles row must not grant anything.
    db.session.add(UserRole(user_id=user_b.id, role_id=role_a.id))
    db.session.commit()
    with app.test_request_context("/"):
        g.user = user_b
        assert user_has_permission("store.orders.read") is False

    # Ownership validation in the service: user belongs to another tenant.
    with pytest.raises(AuthorizationError):
        AuthService().assign_role(
            tenant_id=tenant_b.id, user_id=user_a.id, role_code="store_staff"
        )
    # ... and the role belongs to another tenant.
    with pytest.raises(NotFoundError):
        AuthService().assign_role(
            tenant_id=tenant_b.id, user_id=user_b.id, role_code="store_staff"
        )


def test_superuser_bypasses_all_permission_checks(app):
    admin = AuthService().register_super_admin(
        email="rbac-owner@azadexa.com", password="password123"
    )
    with app.test_request_context("/"):
        g.user = admin
        for code in (
            "store.orders.read",
            "tenant.orders.read",
            "platform.settings.write",
        ):
            assert user_has_permission(code) is True
            require_permission(code)


def test_assign_role_endpoint_is_platform_admin_only(
    app, client, platform_admin_headers
):
    tenant = _tenant("API Store", "rbac-api-store", "api@rbac.com")
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="api-customer@rbac.com",
        password="password123",
        is_admin=False,
    )
    _seed_role(tenant.id, "store_staff", "store.orders.read")
    url = f"/api/v1/users/{customer.public_id}/roles"
    payload = {"role_code": "store_staff", "tenant_id": tenant.id}

    assert client.post(url, json=payload).status_code == 401

    ok = client.post(url, json=payload, headers=platform_admin_headers)
    assert ok.status_code == 201
    assert ok.get_json()["role"]["code"] == "store_staff"

    other_tenant = _tenant("Other Store", "rbac-other-store", "other@rbac.com")
    cross = client.post(
        url,
        json={"role_code": "store_staff", "tenant_id": other_tenant.id},
        headers=platform_admin_headers,
    )
    assert cross.status_code == 403
