from __future__ import annotations

import os

import pytest

from auth.auth_service import AuthService
from core.utils import utc_now
from platform_models.audit_log import AuditLog
from platform_models.impersonation_session import ImpersonationSession
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService
from user.user import User

PLATFORM_LOGIN = "/api/v1/auth/login"
START = "/api/v1/platform/impersonation/start"
END = "/api/v1/platform/impersonation/end"
STATUS = "/api/v1/platform/impersonation/status"


@pytest.fixture
def setup(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="ImpersonT",
        slug="imperson-t",
        email="owner@impersont.com",
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
    return {
        "app": app,
        "admin": admin,
        "tenant": tenant,
        "target": target,
    }


def _login(client, email, password, tenant_slug=None):
    payload = {"email": email, "password": password}
    if tenant_slug:
        payload["tenant_id"] = tenant_slug
    return client.post(PLATFORM_LOGIN, json=payload)


def _impersonation_headers(app, user, *, tenant_slug=None):
    from support.http import auth_headers

    return auth_headers(user, app=app, tenant_id=tenant_slug)


def test_debug_endpoint_flow(client, setup):
    print("\n=== APP CONFIG DB URI ===")
    print(setup["app"].config.get("SQLALCHEMY_DATABASE_URI"))
    print("\n=== ROUTES ===")
    for rule in sorted(setup["app"].url_map.iter_rules(), key=lambda r: r.rule):
        if (
            "/impersonation/" in rule.rule
            or "health" in rule.rule
            or "auth/login" in rule.rule
        ):
            print(rule.rule, rule.endpoint, list(rule.methods))
    _login(client, setup["admin"].email, "password123")
    headers = _impersonation_headers(setup["app"], setup["admin"])
    for name, path in [
        ("START", START),
        ("END", END),
        ("STATUS", STATUS),
        ("LOGIN", PLATFORM_LOGIN),
    ]:
        if name == "START":
            resp = client.post(
                path, json={"target_user_id": setup["target"].id}, headers=headers
            )
        elif name == "END":
            resp = client.post(path, headers=headers)
        elif name == "STATUS":
            resp = client.get(path, headers=headers)
        else:
            resp = client.post(
                path, json={"email": setup["admin"].email, "password": "password123"}
            )
        print(
            name, path, resp.status_code, resp.get_json(silent=True) or resp.data[:300]
        )
    with setup["app"].app_context():
        print("\n=== COUNTS ===")
        print(
            "users",
            User.query.count(),
            "sessions",
            ImpersonationSession.query.count(),
            "audits",
            AuditLog.query.count(),
        )
