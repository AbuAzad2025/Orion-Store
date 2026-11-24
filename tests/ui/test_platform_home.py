"""Public platform landing page — i18n, unique actions, active store banners."""

from __future__ import annotations

from tenant_svc.tenant_service import TenantService


def test_platform_home_arabic_default(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(
            name="My Store", slug="mystore", email="m@store.test"
        )
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert '<html lang="ar" dir="rtl">' in text
    assert "متجرك الإلكتروني، جاهز للانطلاق" in text
    assert "دخول المنصة" in text and "دخول المتجر" in text
    assert "🧱 أنشئ متجرك الخاص" in text and "❤️ تبرع لنا" in text
    assert "My Store" in text and "mystore.azadexa.com" in text
    # Exactly one language switch, no duplicate login/donate actions.
    assert text.count('class="orion-locale-switch"') == 1
    assert text.count("تبرع لنا") == 1
    assert text.count("أنشئ متجرك الخاص") == 1


def test_platform_home_english_locale(client, app) -> None:
    resp = client.get("/?locale=en")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in text
    assert "Your online store, ready to launch" in text
    assert "Platform admin" in text and "Store admin" in text
    assert "Create your store" in text and "Donate to us" in text
    assert "Browse the store" in text
    assert "متجرك الإلكتروني" not in text


def test_platform_home_inactive_store_hidden(client, app) -> None:
    from orion.extensions import db

    with app.app_context():
        inactive = TenantService().create_tenant(
            name="Hidden Store", slug="hidden", email="h@store.test"
        )
        inactive.is_active = False
        db.session.commit()
    resp = client.get("/")
    assert "Hidden Store" not in resp.get_data(as_text=True)
