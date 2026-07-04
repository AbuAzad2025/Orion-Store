from __future__ import annotations

import pytest

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_full_routes(app):
    with app.app_context():
        print("\nALL API ROUTES:")
        for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
            if rule.rule.startswith("/api") or rule.rule == "/health":
                print(rule.rule, rule.endpoint, sorted(rule.methods))
        print("\nBLUEPRINTS:")
        for name, bp in app.blueprints.items():
            print(name, bp)
