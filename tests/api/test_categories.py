"""Category API tests (wave 2)."""

from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant_store(app):
    tenants = TenantService()
    auth = AuthService()
    tenant = tenants.create_tenant(
        name="Cat Store", slug="cat-store", email="cat@test.com"
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@cat.com",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def test_create_and_list_categories(client, tenant_store):
    tenant, admin = tenant_store
    headers = auth_headers(admin, tenant_id=tenant.slug)

    create = client.post(
        "/api/v1/categories/",
        headers=headers,
        json={"name": "Electronics", "slug": "electronics"},
    )
    assert create.status_code == 201

    listing = client.get("/api/v1/categories/", headers=headers)
    assert listing.status_code == 200
    assert len(listing.get_json()["categories"]) == 1
