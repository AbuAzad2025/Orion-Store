"""Smoke tests — wave 0 definition of done."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "azadexa-orion"


def test_api_blueprints_registered(client):
    endpoints = [
        "/api/v1/auth/status",
        "/api/v1/store/status",
        "/api/v1/tenant/status",
        "/api/v1/platform/status",
        "/webhooks/status",
    ]
    for path in endpoints:
        response = client.get(path)
        assert response.status_code == 200
        assert response.get_json()["status"] == "pending"
