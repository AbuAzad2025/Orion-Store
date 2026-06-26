"""Middleware pipeline tests (wave 1)."""

from __future__ import annotations

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService


def test_resolve_tenant_from_public_id_header(client):
    tenants = TenantService()
    tenant = tenants.create_tenant(
        name="UUID Store", slug="uuid-store", email="uuid@store.com"
    )
    tenant_id = str(tenant.public_id)
    response = client.get("/api/v1/tenants/me", headers={"X-Tenant-ID": tenant_id})
    assert response.status_code == 200


def test_resolve_tenant_from_subdomain(client):
    tenants = TenantService()
    tenants.create_tenant(
        name="Sub Store", slug="sub-store", email="sub@store.com", domain="substore"
    )
    response = client.get(
        "/api/v1/tenants/me",
        headers={"Host": "substore.azadexa.com"},
    )
    assert response.status_code == 200
    assert response.get_json()["tenant"]["slug"] == "sub-store"


def test_unknown_user_header_returns_401(client):
    response = client.get(
        "/api/v1/tenants/",
        headers={"X-User-ID": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 401


def test_tenant_user_cannot_access_other_tenant(client):
    tenants = TenantService()
    auth = AuthService()
    t1 = tenants.create_tenant(name="A", slug="tenant-a", email="a@test.com")
    t2 = tenants.create_tenant(name="B", slug="tenant-b", email="b@test.com")
    user = auth.register_tenant_user(
        tenant_id=t1.id, email="user@a.com", password="password123"
    )
    user_id = str(user.public_id)
    response = client.get(
        "/api/v1/tenants/me",
        headers={"X-Tenant-ID": t2.slug, "X-User-ID": user_id},
    )
    assert response.status_code == 401
