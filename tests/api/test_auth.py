"""Auth API integration tests (wave 1)."""

from __future__ import annotations


def _headers(user) -> dict[str, str]:
    return {"X-User-ID": user.public_id, "Content-Type": "application/json"}


def test_list_tenants_requires_platform_admin(client):
    response = client.get("/api/v1/tenants/")
    assert response.status_code == 401


def test_register_platform_admin(client):
    response = client.post(
        "/api/v1/auth/register/platform",
        json={"email": "admin@azadexa.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["email"] == "admin@azadexa.com"
    assert data["user"]["is_superuser"] is True


def test_login_superuser(client, platform_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["is_superuser"] is True
    assert "access_token" in data
    assert "refresh_token" in data


def test_bearer_token_lists_tenants(client, platform_admin):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "password123"},
    )
    token = login.get_json()["access_token"]
    from support.http import bearer_headers

    response = client.get("/api/v1/tenants/", headers=bearer_headers(token))
    assert response.status_code == 200


def test_login_invalid_password(client, platform_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_requires_json_body(client):
    response = client.post("/api/v1/auth/login", data="not-json")
    assert response.status_code == 401


def test_list_tenants_as_platform_admin(client, platform_admin):
    create = client.post(
        "/api/v1/tenants/",
        headers=_headers(platform_admin),
        json={
            "name": "Listed Store",
            "slug": "listed-store",
            "email": "listed@store.com",
        },
    )
    assert create.status_code == 201
    response = client.get("/api/v1/tenants/", headers=_headers(platform_admin))
    assert response.status_code == 200
    assert len(response.get_json()["tenants"]) == 1
