"""Product API integration tests (wave 2)."""

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
        name="Catalog Store", slug="catalog-store", email="store@test.com"
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@catalog.com",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def test_product_crud(client, tenant_store):
    tenant, admin = tenant_store
    headers = auth_headers(admin, tenant_id=tenant.slug)

    create = client.post(
        "/api/v1/products/",
        headers=headers,
        json={
            "name": "Test Product",
            "slug": "test-product",
            "price": "19.99",
            "quantity": 10,
            "is_published": True,
        },
    )
    assert create.status_code == 201
    public_id = create.get_json()["product"]["public_id"]

    listing = client.get("/api/v1/products/", headers=headers)
    assert listing.status_code == 200
    assert len(listing.get_json()["products"]) == 1

    get_one = client.get(f"/api/v1/products/{public_id}", headers=headers)
    assert get_one.status_code == 200

    update = client.put(
        f"/api/v1/products/{public_id}",
        headers=headers,
        json={"price": "24.99"},
    )
    assert update.status_code == 200
    assert update.get_json()["product"]["price"] == "24.99"

    delete = client.delete(f"/api/v1/products/{public_id}", headers=headers)
    assert delete.status_code == 200

    listing_after = client.get("/api/v1/products/", headers=headers)
    assert listing_after.get_json()["products"] == []


def test_products_require_tenant_context(client, platform_admin):
    headers = {
        "X-User-ID": platform_admin.public_id,
        "Content-Type": "application/json",
    }
    response = client.get("/api/v1/products/", headers=headers)
    assert response.status_code == 401
