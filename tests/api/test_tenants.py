"""Tenant API integration tests (wave 1)."""

from __future__ import annotations

from support.http import bearer_headers


def _bearer_token_for(app, user) -> dict[str, str]:
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity=str(user.public_id))
    return bearer_headers(token)


def test_create_tenant(client, app, platform_admin):
    headers = _bearer_token_for(app, platform_admin)
    response = client.post(
        "/api/v1/tenants/",
        headers=headers,
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


def test_create_tenant_missing_fields(client, app, platform_admin):
    headers = _bearer_token_for(app, platform_admin)
    response = client.post(
        "/api/v1/tenants/",
        headers=headers,
        json={"name": "Incomplete"},
    )
    assert response.status_code == 400


def test_current_tenant_without_context(client):
    response = client.get("/api/v1/tenants/me")
    assert response.status_code == 404


def test_current_tenant_by_slug_header(client, app, platform_admin):
    headers = _bearer_token_for(app, platform_admin)
    create = client.post(
        "/api/v1/tenants/",
        headers=headers,
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
