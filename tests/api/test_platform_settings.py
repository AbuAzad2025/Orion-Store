"""Platform settings API (wave 2)."""

from __future__ import annotations

from platform_svc.platform_settings_service import PlatformSettingsService


def test_get_platform_settings(client, platform_admin):
    with client.flask_client.application.app_context():
        PlatformSettingsService().ensure_seeded()

    headers = {
        "X-User-ID": platform_admin.public_id,
        "Content-Type": "application/json",
    }
    response = client.get("/api/v1/platform/settings", headers=headers)
    assert response.status_code == 200
    data = response.get_json()["settings"]
    assert data["platform_name"] == "Azadexa"
    assert data["default_commission_percent"] == "0.0100"
