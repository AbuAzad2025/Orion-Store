"""Public platform landing page — i18n, unique actions, active store banners."""

from __future__ import annotations

from tenant_svc.tenant_service import TenantService


def test_platform_home_arabic_default(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(
            name="My Store", slug="mystore", email="m@store.test"
        )
    resp = client.get("/", headers={"Host": "orion.azadexa.com"})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert '<html lang="ar" dir="rtl">' in text
    assert "متجرك الإلكتروني، جاهز للانطلاق" in text
    assert "دخول المنصة" in text and "دخول المتجر" not in text
    assert "🧱 أنشئ متجرك الخاص" in text and "❤️ تبرع لنا" in text
    # One login action only; stores are chosen via search/banner cards.
    assert 'class="orion-access-card"' not in text
    assert "بوابات الدخول" not in text
    assert "account?store=" not in text
    assert 'id="store-search"' in text
    assert "My Store" in text and "/s/mystore/" in text
    # Brand logo at the top-right (RTL start) of the header.
    assert 'class="orion-home-brand"' in text
    assert "azadexa-navbar.png" in text
    # Exactly one language switch, no duplicate login/donate actions.
    assert text.count('class="orion-locale-switch"') == 1
    assert text.count("تبرع لنا") == 1
    assert text.count("أنشئ متجرك الخاص") == 1


def test_platform_home_english_locale(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(
            name="English Store", slug="english-store", email="en@store.test"
        )
    resp = client.get("/?locale=en", headers={"Host": "orion.azadexa.com"})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Platform admin" in text
    assert "Your online store, ready to launch" in text
    assert "Platform admin" in text and "Store admin" not in text
    assert "Create your store" in text and "Donate to us" in text
    assert 'id="store-search"' in text
    assert "متجرك الإلكتروني" not in text


def test_store_domain_root_is_storefront_not_landing(client, app) -> None:
    """A store subdomain must show the storefront, never the platform landing."""
    from catalog_svc.product_service import ProductService

    with app.app_context():
        tenant = TenantService().create_tenant(
            name="Root Store", slug="rootstore", email="r@store.test"
        )
        ProductService().create(
            tenant_id=tenant.id,
            name="Visible Product",
            slug="visible",
            price="10.00",
            is_published=True,
        )
    resp = client.get("/", headers={"Host": "rootstore.azadexa.com"})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Visible Product" in text
    assert "بوابات الدخول" not in text
    assert "orion-access-card" not in text


def test_platform_home_inactive_store_hidden(client, app) -> None:
    from orion.extensions import db

    with app.app_context():
        inactive = TenantService().create_tenant(
            name="Hidden Store", slug="hidden", email="h@store.test"
        )
        inactive.is_active = False
        db.session.commit()
    resp = client.get("/", headers={"Host": "orion.azadexa.com"})
    assert "Hidden Store" not in resp.get_data(as_text=True)
