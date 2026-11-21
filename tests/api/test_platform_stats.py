"""Platform dashboard stats reflect real database state."""

from __future__ import annotations

from tenant_svc.tenant_service import TenantService


def test_platform_stats_count_real_tenants_and_users(
    client, app, platform_admin_headers
) -> None:
    tenants = TenantService()
    with app.app_context():
        tenants.create_tenant(name="Stats A", slug="stats-a", email="a@stats.test")
        tenants.create_tenant(name="Stats B", slug="stats-b", email="b@stats.test")

    response = client.get("/api/v1/platform/stats", headers=platform_admin_headers)
    assert response.status_code == 200
    stats = response.get_json()["stats"]

    assert stats["tenants"] == 2
    assert stats["active_tenants"] == 2
    assert stats["users"] >= 1  # platform admin created by fixture
    assert stats["active_users"] >= 1


def test_platform_stats_requires_platform_admin(client, app) -> None:
    response = client.get("/api/v1/platform/stats")
    assert response.status_code in (401, 403)
