"""Tenant API integration tests (wave 1)."""

from __future__ import annotations


def _headers(user) -> dict[str, str]:
    return {"X-User-ID": user.public_id, "Content-Type": "application/json"}


def test_create_tenant(client, platform_admin):
    response = client.post(
        "/api/v1/tenants/",
        headers=_headers(platform_admin),
        json={
            "name": "Demo Store",
            "slug": "demo-store",
            "email": "demo@store.com",
            "admin_email": "admin@demo.com",
            "admin_password": "password123",
        },
    )
    assert response.status_code == 201
    tenant = response.get_json()["tenant"]
    assert tenant["slug"] == "demo-store"


def test_create_tenant_missing_fields(client, platform_admin):
    response = client.post(
        "/api/v1/tenants/",
        headers=_headers(platform_admin),
        json={"name": "Incomplete"},
    )
    assert response.status_code == 400


def test_current_tenant_without_context(client):
    response = client.get("/api/v1/tenants/me")
    assert response.status_code == 404


def test_current_tenant_by_slug_header(client, platform_admin):
    create = client.post(
        "/api/v1/tenants/",
        headers=_headers(platform_admin),
        json={
            "name": "Header Store",
            "slug": "header-store",
            "email": "header@store.com",
        },
    )
    slug = create.get_json()["tenant"]["slug"]
    response = client.get("/api/v1/tenants/me", headers={"X-Tenant-ID": slug})
    assert response.status_code == 200
    assert response.get_json()["tenant"]["slug"] == "header-store"
