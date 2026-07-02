"""Middleware pipeline tests (wave 1).

AZ-0.2: X-User-ID header is completely removed. All identity comes from
JWT Bearer tokens (API) or server-side sessions (HTML admin).
"""

from __future__ import annotations

from flask_jwt_extended import create_access_token

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


def test_x_user_id_no_longer_honored(client, app):
    """AZ-0.2: X-User-ID header is completely ignored — anonymous request
    returns 401 even with a valid user public_id in the header."""
    from auth.auth_service import AuthService
    from tenant_svc.tenant_service import TenantService

    tenants = TenantService()
    tenant = tenants.create_tenant(
        name="X-ID Store", slug="xid-store", email="xid@store.com"
    )
    auth = AuthService()
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@xid.com",
        password="password123",
        is_admin=True,
    )
    user_id = str(admin.public_id)
    # X-User-ID is ignored — no Bearer token, so request is anonymous
    # /api/v1/tenants/ requires platform-admin auth, so anonymous = 401
    response = client.get(
        "/api/v1/tenants/",
        headers={"X-User-ID": user_id},
    )
    assert response.status_code == 401


def test_anonymous_request_returns_401(client):
    """Unauthenticated requests to protected endpoints fail."""
    response = client.get("/api/v1/tenants/")
    assert response.status_code == 401


def test_bearer_token_authenticates(client, app):
    """JWT Bearer token still works for authentication."""
    from auth.auth_service import AuthService

    tenants = TenantService()
    tenant = tenants.create_tenant(
        name="Bearer Store", slug="bearer-store", email="bearer@store.com"
    )
    auth = AuthService()
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@bearer.com",
        password="password123",
        is_admin=True,
    )
    with app.app_context():
        token = create_access_token(identity=str(admin.public_id))
    from support.http import bearer_headers

    headers = bearer_headers(token, tenant_id=tenant.slug)
    response = client.get("/api/v1/tenants/me", headers=headers)
    assert response.status_code == 200
