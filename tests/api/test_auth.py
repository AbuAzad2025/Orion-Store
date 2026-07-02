"""Auth API integration tests (wave 1).

AZ-0.1: Public platform-admin registration is permanently disabled.
Platform administrators are created only through the secure CLI bootstrap
(``scripts/bootstrap_cli.py``) or by existing platform administrators through
authenticated internal services.
"""

from __future__ import annotations

from orion.extensions import db


def _headers(user) -> dict[str, str]:
    # NOTE: X-User-ID will be removed in AZ-0.2.
    return {"X-User-ID": user.public_id, "Content-Type": "application/json"}


def _create_tenant_and_admin(app) -> object:
    """Trusted internal helper: creates a tenant and a tenant-admin user.

    Returns a SimpleNamespace with ``public_id`` and ``email`` suitable for
    ``bearer_headers()``.
    """
    from types import SimpleNamespace

    from auth.auth_service import AuthService
    from tenant_svc.tenant_service import TenantService

    tenant = TenantService().create_tenant(
        name="Test Tenant",
        slug="test-tenant",
        email="test@tenant.com",
    )
    auth = AuthService()
    user = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="tenant-admin@test.azadexa.com",
        password="password123",
        is_admin=True,
    )
    return SimpleNamespace(public_id=str(user.public_id), email=user.email)


# ── AZ-0.1: Public route permanently disabled ──────────────────────────


def test_register_platform_admin_anonymous_rejected(client):
    """Anonymous HTTP requests cannot create a platform administrator."""
    response = client.post(
        "/api/v1/auth/register/platform",
        json={"email": "anon@platform.com", "password": "password123"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def _bearer_token_for(app, user) -> dict[str, str]:
    """Create Bearer auth headers for a test user (no X-User-ID)."""
    from flask_jwt_extended import create_access_token
    from support.http import bearer_headers

    with app.app_context():
        token = create_access_token(identity=str(user.public_id))
    return bearer_headers(token)


def test_register_platform_admin_authenticated_user_rejected(client):
    """An authenticated non-platform-admin cannot register one either."""
    with client.app.app_context():
        tenant_admin = _create_tenant_and_admin(client.app)
        headers = _bearer_token_for(client.app, tenant_admin)

    response = client.post(
        "/api/v1/auth/register/platform",
        headers=headers,
        json={"email": "auth-user@platform.com", "password": "password123"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_register_platform_admin_tenant_admin_rejected(client):
    """A tenant administrator cannot escalate to platform admin through the
    public route, even with an authenticated session."""
    with client.app.app_context():
        tenant_admin = _create_tenant_and_admin(client.app)
        headers = _bearer_token_for(client.app, tenant_admin)

    response = client.post(
        "/api/v1/auth/register/platform",
        headers=headers,
        json={"email": "tenant-admin@platform.com", "password": "password123"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_register_platform_admin_privileged_fields_rejected(client):
    """Privileged fields in the request payload cannot create a platform
    administrator — the route is unconditionally disabled."""
    payloads = [
        {"email": "hacker1@platform.com", "password": "password123",
         "is_superuser": True},
        {"email": "hacker2@platform.com", "password": "password123",
         "is_platform_admin": True},
        {"email": "hacker3@platform.com", "password": "password123",
         "is_owner": True},
        {"email": "hacker4@platform.com", "password": "password123",
         "role": "superadmin"},
    ]
    for payload in payloads:
        response = client.post(
            "/api/v1/auth/register/platform",
            json=payload,
        )
        assert response.status_code == 404, f"Payload {payload!r} bypassed protection!"
        data = response.get_json()
        assert "error" in data


def test_register_platform_admin_no_creation_after_bootstrap(client):
    """Once a platform administrator exists via bootstrap, no HTTP request
    can create another."""
    from auth.auth_service import AuthService

    with client.app.app_context():
        # Ensure no platform admin exists
        from user.user import User

        User.query.filter_by(email="bootstrap-test@platform.com",
                             tenant_id=None).delete()
        db.session.commit()

        # Bootstrap first admin via trusted internal path
        auth_service = AuthService()
        admin = auth_service.register_super_admin(
            email="bootstrap-test@platform.com", password="password123"
        )
        assert admin is not None
        assert admin.is_superuser is True

    # Now the HTTP route must reject
    response = client.post(
        "/api/v1/auth/register/platform",
        json={
            "email": "second-admin@platform.com",
            "password": "password123",
        },
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_register_platform_admin_empty_body(client):
    """Even an empty body must not crash or create an admin."""
    response = client.post(
        "/api/v1/auth/register/platform",
        json={},
    )
    assert response.status_code == 404


def test_register_platform_admin_missing_body(client):
    """A completely missing JSON body must not crash or create an admin."""
    response = client.post(
        "/api/v1/auth/register/platform",
        data="",
        content_type="application/json",
    )
    assert response.status_code == 404


# ── Bootstrap helper behaviour (trusted internal path) ─────────────────


def test_bootstrap_creates_first_admin_when_none_exists(client):
    """The trusted bootstrap path (``AuthService.register_super_admin``)
    creates the first platform administrator when no other exists."""
    from auth.auth_service import AuthService
    from user.user import User

    with client.app.app_context():
        User.query.filter_by(email="first@bootstrap.com",
                             tenant_id=None).delete()
        db.session.commit()

        admin = AuthService().register_super_admin(
            email="first@bootstrap.com", password="password123"
        )
        assert admin.is_superuser is True
        assert admin.email == "first@bootstrap.com"


def test_bootstrap_blocked_when_admin_exists(client):
    """The trusted bootstrap path refuses to create a second platform
    administrator when the same email is used."""
    from auth.auth_service import AuthService
    from user.user import User
    from core.exceptions import ValidationError

    with client.app.app_context():
        User.query.filter_by(email="existing@bootstrap.com",
                             tenant_id=None).delete()
        db.session.commit()

        AuthService().register_super_admin(
            email="existing@bootstrap.com", password="password123"
        )

        import pytest
        with pytest.raises(ValidationError, match="Super admin already exists"):
            AuthService().register_super_admin(
                email="existing@bootstrap.com", password="password123"
            )


# ── Existing auth tests (unchanged) ───────────────────────────────────


def test_list_tenants_requires_platform_admin(client):
    response = client.get("/api/v1/tenants/")
    assert response.status_code == 401


def test_login_superuser(client, platform_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["is_superuser"] is True
    assert "access_token" in data
    assert "refresh_token" in data


def test_bearer_token_lists_tenants(client, platform_admin):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "password123"},
    )
    token = login.get_json()["access_token"]
    from support.http import bearer_headers

    response = client.get("/api/v1/tenants/", headers=bearer_headers(token))
    assert response.status_code == 200


def test_refresh_token(client, platform_admin):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "password123"},
    )
    refresh = login.get_json()["refresh_token"]
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert response.status_code == 200
    assert "access_token" in response.get_json()


def test_login_invalid_password(client, platform_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@azadexa.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_requires_json_body(client):
    response = client.post("/api/v1/auth/login", data="not-json")
    assert response.status_code == 401


def test_list_tenants_as_platform_admin(client, platform_admin):
    create = client.post(
        "/api/v1/tenants/",
        headers=_headers(platform_admin),
        json={
            "name": "Listed Store",
            "slug": "listed-store",
            "email": "listed@store.com",
        },
    )
    assert create.status_code == 201
    response = client.get("/api/v1/tenants/", headers=_headers(platform_admin))
    assert response.status_code == 200
    assert len(response.get_json()["tenants"]) == 1
