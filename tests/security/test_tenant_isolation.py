"""Tenant isolation security tests (§0.8, wave 1 #18)."""

from __future__ import annotations

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService


def test_tenant_a_cannot_see_tenant_b_users(app):
    tenants = TenantService()
    auth = AuthService()

    t1 = tenants.create_tenant(name="Store A", slug="store-a", email="a@test.com")
    t2 = tenants.create_tenant(name="Store B", slug="store-b", email="b@test.com")
    auth.register_tenant_user(
        tenant_id=t1.id, email="admin@a.com", password="password123"
    )
    auth.register_tenant_user(
        tenant_id=t2.id, email="admin@b.com", password="password123"
    )

    users_a = tenants.list_users_for_tenant(t1.id)
    users_b = tenants.list_users_for_tenant(t2.id)

    assert len(users_a) == 1
    assert len(users_b) == 1
    assert users_a[0].email == "admin@a.com"
    assert users_b[0].email == "admin@b.com"
    assert all(u.tenant_id == t1.id for u in users_a)
    assert all(u.tenant_id == t2.id for u in users_b)


def test_superuser_has_no_tenant_id(app):
    auth = AuthService()
    admin = auth.register_super_admin(
        email="owner@azadexa.com", password="password123"
    )
    assert admin.is_superuser is True
    assert admin.tenant_id is None
    assert admin.is_customer is False
