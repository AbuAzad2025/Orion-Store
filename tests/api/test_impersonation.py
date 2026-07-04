"""Integrations tests for platform-admin impersonation (AZ-0.18).

Covers:
  - successful start/end cycle
  - unauthorized entry attempts
  - expiration windows
  - audit log row validation
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from auth.auth_service import AuthService
from core.utils import utc_now
from orion.extensions import db
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
    resp = client.post(PLATFORM_LOGIN, json=payload)
    assert resp.status_code == 200, resp.get_json()
    return resp


def _impersonation_headers(app, user, *, tenant_slug=None):
    from flask_jwt_extended import create_access_token

    claims = {
        "is_superuser": getattr(user, "is_superuser", True),
        "tenant_id": getattr(user, "tenant_id", None),
        "is_admin": getattr(user, "is_admin", True),
    }
    token = create_access_token(identity=str(user.public_id), additional_claims=claims)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if tenant_slug:
        headers["X-Tenant-ID"] = tenant_slug
    return headers


class TestImpersonationStartEnd:
    def test_start_returns_session(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        resp = client.post(
            START, json={"target_user_id": setup["target"].id}, headers=headers
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["session"]["target_user_id"] == setup["target"].id

    def test_successful_start_then_end_cycle(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        start = client.post(
            START, json={"target_user_id": setup["target"].id}, headers=headers
        )
        assert start.status_code == 200
        with setup["app"].app_context():
            assert (
                ImpersonationSession.query.filter_by(
                    impersonator_user_id=setup["admin"].id,
                    target_user_id=setup["target"].id,
                ).count()
                == 1
            )
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        end = client.post(END, headers=headers)
        assert end.status_code == 200
        with setup["app"].app_context():
            assert (
                ImpersonationSession.query.filter_by(
                    impersonator_user_id=setup["admin"].id,
                    target_user_id=setup["target"].id,
                    revoked=True,
                ).count()
                >= 1
            )

    def test_end_response_message(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(START, json={"target_user_id": setup["target"].id}, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        end = client.post(END, headers=headers)
        assert end.status_code == 200
        body = end.get_json()
        assert body["message"] == "Impersonation ended"

    def test_duplicate_start_returns_conflict(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        first = client.post(
            START, json={"target_user_id": setup["target"].id}, headers=headers
        )
        assert first.status_code == 200
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        second = client.post(
            START, json={"target_user_id": setup["target"].id}, headers=headers
        )
        assert second.status_code == 409

    def test_start_denies_non_admin(self, client, setup):
        _login(
            client,
            setup["target"].email,
            "password123",
            tenant_slug=setup["tenant"].slug,
        )
        headers = _impersonation_headers(
            setup["app"], setup["target"], tenant_slug=setup["tenant"].slug
        )
        resp = client.post(
            START, json={"target_user_id": setup["target"].id}, headers=headers
        )
        assert resp.status_code in (401, 403)


class TestImpersonationExpiration:
    def test_status_shows_active_session(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(START, json={"target_user_id": setup["target"].id}, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        resp = client.get(STATUS, headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["active"] is True

    def test_status_reports_inactive_after_expiry(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(START, json={"target_user_id": setup["target"].id}, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        with setup["app"].app_context():
            session = ImpersonationSession.query.filter_by(
                impersonator_user_id=setup["admin"].id,
                target_user_id=setup["target"].id,
            ).first()
            session.expires_at = utc_now() - timedelta(minutes=1)
            db.session.commit()
        resp = client.get(STATUS, headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["active"] is False


class TestImpersonationAuditValidation:
    def test_start_creates_impersonation_start_audit_row(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(START, json={"target_user_id": setup["target"].id}, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        with setup["app"].app_context():
            row = AuditLog.query.filter_by(action="impersonation_start").first()
            assert row is not None
            assert row.actor_user_id == setup["admin"].id
            assert row.details is not None

    def test_end_creates_impersonation_end_audit_row(self, client, setup):
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(START, json={"target_user_id": setup["target"].id}, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        client.post(END, headers=headers)
        _login(client, setup["admin"].email, "password123")
        headers = _impersonation_headers(setup["app"], setup["admin"])
        with setup["app"].app_context():
            row = AuditLog.query.filter_by(action="impersonation_end").first()
            assert row is not None
            assert row.actor_user_id == setup["admin"].id
