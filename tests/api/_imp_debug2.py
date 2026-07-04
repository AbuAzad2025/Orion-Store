from __future__ import annotations

import os

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

BASE = "/api/v1/platform/impersonation"


@pytest.fixture
def setup(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="ImpersonT", slug="imperson-t", email="owner@impersont.com"
    )
    target = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="tenant_admin@impersont.com",
        password="password123",
        is_admin=True,
    )
    admin = AuthService().register_super_admin(
        email="owner@azadexa.com", password="password123"
    )
    return {"app": app, "admin": admin, "target": target, "tenant": tenant}


def _login(client, email, password):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def test_404_debug(client, setup):
    _login(client, setup["admin"].email, "password123")
    headers = auth_headers(setup["admin"], app=setup["app"])
    cases = [
        (
            "POST START",
            f"{BASE}/start",
            {"json": {"target_user_id": setup["target"].id}, "headers": headers},
        ),
        ("GET STATUS", f"{BASE}/status", {"headers": headers}),
        ("POST END", f"{BASE}/end", {"headers": headers}),
        ("GET health", "/health", {}),
        (
            "POST login",
            "/api/v1/auth/login",
            {"json": {"email": setup["admin"].email, "password": "password123"}},
        ),
    ]
    for name, path, kwargs in cases:
        r = (
            client.post(path, **kwargs)
            if name.startswith("POST") and "login" in name
            else client.post(path, **kwargs)
        )
        if name != "GET health" and not name.endswith("login"):
            method = path
            if name == "GET STATUS":
                r = client.get(path, **kwargs)
        body = r.get_json(silent=True)
        print(
            name,
            path,
            r.status_code,
            (
                body
                if body is not None
                else r.data.decode("utf-8", errors="replace")[:400]
            ),
        )
    with setup["app"].app_context():
        print("\nROUTES:")
        for rule in sorted(setup["app"].url_map.iter_rules(), key=lambda x: x.rule):
            if any(x in rule.rule for x in ["impersonation", "health", "auth/login"]):
                print(rule.rule, rule.endpoint, list(rule.methods))
