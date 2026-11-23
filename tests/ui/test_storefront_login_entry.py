"""Unified sign-in entry in the storefront navbar and dedicated login page."""

from __future__ import annotations

import pytest

from core.store_token import issue
from support.http import tenant_headers
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    with app.app_context():
        return TenantService().create_tenant(
            name="Login Store",
            slug="login-store",
            email="login@test.com",
            domain="demo",
        )


def test_login_page_links_both_destinations(client, app, store) -> None:
    with app.app_context():
        token = issue(store)

    response = client.get(
        f"/login?store={token}",
        headers=tenant_headers(store.slug),
        base_url="https://demo.azadexa.com",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Arabic UI with both choices.
    assert "تسجيل الدخول" in html
    assert "حسابي (الزبون)" in html
    assert "لوحة المتجر" in html
    assert "لوحة المنصة" in html

    # Customer login keeps the signed store token.
    assert f"/account?store={token}" in html

    # Store admin is routed to this store's own subdomain (Host-derived), and
    # the platform admin keeps a separate URL.
    assert "https://demo.azadexa.com/admin/login" in html
    assert "https://orion.azadexa.com/admin/login" in html


def test_navbar_has_login_button(client, app, store) -> None:
    with app.app_context():
        token = issue(store)

    response = client.get(
        f"/?store={token}",
        headers=tenant_headers(store.slug),
        base_url="https://demo.azadexa.com",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="orion-nav-login"' in html
    assert "/login?store=" in html


def test_login_page_requires_tenant(client, app, monkeypatch) -> None:
    monkeypatch.setitem(app.config, "DEBUG", False)
    response = client.get("/login")
    assert response.status_code == 404
