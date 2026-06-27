"""Storefront cart API coverage (wave 3)."""

from __future__ import annotations

from support.http import tenant_headers

from tenant_svc.tenant_service import TenantService


def test_create_cart_and_get_empty(client, app):
    tenant = TenantService().create_tenant(
        name="SF", slug="sf-store", email="sf@test.com"
    )
    headers = tenant_headers(tenant.slug)
    create = client.post("/api/v1/store/cart", headers=headers)
    assert create.status_code == 201
    token = create.get_json()["cart"]["cart_token"]
    get_resp = client.get(f"/api/v1/store/cart/{token}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["items"] == []


def test_get_cart_not_found(client, app):
    tenant = TenantService().create_tenant(
        name="SF404", slug="sf404", email="sf404@test.com"
    )
    headers = tenant_headers(tenant.slug)
    response = client.get("/api/v1/store/cart/bad-token", headers=headers)
    assert response.status_code == 404
