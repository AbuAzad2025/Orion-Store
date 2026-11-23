"""Store-admin HTML login must resolve the tenant from the Host when no slug is typed.

Regression guard for the bug where :func:`authenticate` with ``tenant_id=None``
only matches platform superusers, so a store admin got 401 on their own domain.
"""

from __future__ import annotations

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService

STORE_DOMAIN = "https://demo.azadexa.com"
STORE_HOST = "demo.azadexa.com"
ADMIN_DOMAIN = "https://orion.azadexa.com"


def _seed_store(app):
    with app.app_context():
        tenant = TenantService().create_tenant(
            name="Demo Store", slug="demo", email="demo@test.local"
        )
        AuthService().register_tenant_user(
            tenant_id=tenant.id,
            email="admin@gulf.test",
            password="password123",
            is_admin=True,
        )
        return tenant.id


def _login(client, email, password, slug="", base_url=STORE_DOMAIN):
    return client.post(
        "/admin/login",
        data={"email": email, "password": password, "tenant_slug": slug},
        base_url=base_url,
    )


def _assert_landing(client, response, expected_path, expected_title, base_url):
    assert response.status_code == 302
    assert response.headers["Location"].endswith(expected_path)
    dash = client.get(expected_path, base_url=base_url, follow_redirects=False)
    assert dash.status_code == 200
    assert expected_title in dash.get_data(as_text=True)


def test_store_admin_logs_in_on_own_domain_without_slug(client, app) -> None:
    _seed_store(app)

    response = _login(client, "admin@gulf.test", "password123")
    _assert_landing(
        client, response, "/admin/store/dashboard", "لوحة المتجر", STORE_DOMAIN
    )


def test_platform_admin_still_logs_in_from_store_domain(
    client, app, platform_admin
) -> None:
    _seed_store(app)

    response = _login(client, "owner@azadexa.com", "password123")
    _assert_landing(
        client, response, "/admin/platform/dashboard", "لوحة المنصة", STORE_DOMAIN
    )


def test_explicit_slug_still_works_from_any_domain(client, app) -> None:
    _seed_store(app)

    response = _login(
        client, "admin@gulf.test", "password123", slug="demo", base_url=ADMIN_DOMAIN
    )
    _assert_landing(
        client, response, "/admin/store/dashboard", "لوحة المتجر", ADMIN_DOMAIN
    )


def test_wrong_password_rejected_on_store_domain(client, app) -> None:
    _seed_store(app)

    response = _login(client, "admin@gulf.test", "wrong-password")
    assert response.status_code == 401


def test_other_tenant_admin_cannot_log_in_via_host_without_slug(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(
            name="Demo Store", slug="demo", email="demo@test.local"
        )
        other = TenantService().create_tenant(
            name="Other Store", slug="other", email="other@test.local"
        )
        AuthService().register_tenant_user(
            tenant_id=other.id,
            email="otheradmin@test.local",
            password="password123",
            is_admin=True,
        )

    response = _login(client, "otheradmin@test.local", "password123")
    assert response.status_code == 401
