"""Platform settings API (wave 2)."""

from __future__ import annotations

from flask_jwt_extended import create_access_token
from platform_svc.platform_settings_service import PlatformSettingsService
from support.http import bearer_headers


def test_get_platform_settings(client, app, platform_admin):
    with client.flask_client.application.app_context():
        PlatformSettingsService().ensure_seeded()

    with app.app_context():
        token = create_access_token(identity=str(platform_admin.public_id))
    headers = bearer_headers(token)
    response = client.get("/api/v1/platform/settings", headers=headers)
    assert response.status_code == 200
    data = response.get_json()["settings"]
    assert data["platform_name"] == "Azadexa"
    assert data["default_commission_percent"] == "0.0100"
