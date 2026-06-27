"""Smoke tests — wave 0 definition of done."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "azadexa-orion"
    assert "redis" in data


def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"
    assert data["database"] is True


def test_api_blueprints_registered(client):
    statuses = {
        "/api/v1/store/status": "active",
        "/api/v1/platform/status": "pending",
        "/webhooks/status": "active",
    }
    for path, expected in statuses.items():
        response = client.get(path)
        assert response.status_code == 200
        assert response.get_json()["status"] == expected
