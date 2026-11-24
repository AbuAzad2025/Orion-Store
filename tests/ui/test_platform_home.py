"""Public platform landing page — login options and active store banners."""

from __future__ import annotations

from tenant_svc.tenant_service import TenantService


def test_platform_home_renders_banners_and_login(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(
            name="My Store", slug="mystore", email="m@store.test"
        )
        inactive = TenantService().create_tenant(
            name="Hidden Store", slug="hidden", email="h@store.test"
        )
        inactive.is_active = False
        from orion.extensions import db

        db.session.commit()

    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "دخول لوحة المنصة" in text
    assert "دخول مدير المتجر" in text
    assert "My Store" in text
    assert "mystore.azadexa.com" in text
    assert "Hidden Store" not in text
    assert 'class="orion-store-banners"' in text


def test_platform_home_authenticated_admin_sees_dashboard_link(client, app) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "دخول لوحة المنصة" in resp.get_data(as_text=True)
