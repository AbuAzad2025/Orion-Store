"""Wave 7 API tests — i18n + feature flags."""

from __future__ import annotations

from feature_flag_svc.feature_flag_service import FeatureFlagService
from i18n_svc.i18n_service import I18nService
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_i18n_languages_api(client, app):
    I18nService().ensure_locales_seeded()
    res = client.get("/api/v1/i18n/languages")
    assert res.status_code == 200
    codes = {lang["code"] for lang in res.get_json()["languages"]}
    assert "ar" in codes and "en" in codes


def test_feature_flags_api_and_admin_page(client, app):
    PlatformSettingsService().ensure_seeded()
    FeatureFlagService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="FF API", slug="ff-api", email="ffa@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@ffa.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    listed = client.get("/api/v1/tenant/feature-flags", headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()["flags"]) >= 3

    updated = client.put(
        "/api/v1/tenant/feature-flags/multi_language",
        headers=headers,
        json={"value": True},
    )
    assert updated.status_code == 200
    assert updated.get_json()["flag"]["value"] is True

    page = client.get(
        "/admin/store/feature-flags",
        headers=headers,
    )
    assert page.status_code == 200
    assert "feature-flags-list" in page.get_data(as_text=True)


def test_product_translation_api(client, app):
    PlatformSettingsService().ensure_seeded()
    I18nService().ensure_locales_seeded()
    tenant = TenantService().create_tenant(
        name="Trans API", slug="trans-api", email="ta@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@ta.com",
        password="password123",
        is_admin=True,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Original",
        slug="original",
        price="12.00",
        is_published=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    put = client.put(
        f"/api/v1/tenant/products/{product.public_id}/translations/en",
        headers=headers,
        json={"name": "Translated"},
    )
    assert put.status_code == 200

    listed = client.get(
        f"/api/v1/tenant/products/{product.public_id}/translations",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.get_json()["translations"][0]["name"] == "Translated"

    FeatureFlagService().set_tenant_override(
        tenant_id=tenant.id, code="multi_language", value=True
    )
    store = client.get(
        f"/api/v1/store/products/{product.slug}?locale=en",
        headers=tenant_headers(tenant.slug),
    )
    assert store.get_json()["product"]["name"] == "Translated"
