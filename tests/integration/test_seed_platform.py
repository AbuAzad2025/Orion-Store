"""Platform settings seed (wave 2 #20)."""

from __future__ import annotations

from platform_svc.platform_settings_service import PlatformSettingsService


def test_ensure_seeded_creates_singleton(app):
    with app.app_context():
        row = PlatformSettingsService().ensure_seeded()
        assert row.platform_name == "Azadexa"
        assert str(row.default_commission_percent) == "0.0100"
        assert row.owner_name == "Ahmad Ghannam"
        again = PlatformSettingsService().ensure_seeded()
        assert again.id == row.id
