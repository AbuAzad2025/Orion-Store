"""Translation service unit tests (wave 7)."""

from __future__ import annotations

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from i18n_svc.i18n_service import I18nService
from i18n_svc.translation_service import TranslationService
from tenant_svc.tenant_service import TenantService


def test_product_translation_merge(app):
    I18nService().ensure_locales_seeded()
    tenant = TenantService().create_tenant(
        name="Trans Co", slug="trans-co", email="tr@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Arabic Name",
        slug="arabic-name",
        price="10.00",
        is_published=True,
    )
    translations = TranslationService()
    translations.upsert_product_translation(
        tenant_id=tenant.id,
        product=product,
        locale="en",
        name="English Name",
        description="English desc",
    )
    merged = translations.merge_product(product, "en")
    assert merged["name"] == "English Name"
    assert merged["locale"] == "en"


def test_category_localized_slug(app):
    I18nService().ensure_locales_seeded()
    tenant = TenantService().create_tenant(
        name="Cat Loc", slug="cat-loc", email="cl@test.com"
    )
    category = CategoryService().create(
        tenant_id=tenant.id, name="فئة", slug="cat-ar"
    )
    translations = TranslationService()
    translations.upsert_category_translation(
        tenant_id=tenant.id,
        category=category,
        locale="en",
        name="Category EN",
        slug="cat-en",
    )
    found = translations.get_category_by_localized_slug(tenant.id, "cat-en", "en")
    assert found.id == category.id
    merged = translations.merge_category(category, "en")
    assert merged["name"] == "Category EN"
    assert merged["slug"] == "cat-en"


def test_feature_flag_blocks_extra_locale(app, client):
    I18nService().ensure_locales_seeded()
    FeatureFlagService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Flag Locale", slug="flag-locale", email="fl@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Base",
        slug="base-prod",
        price="5.00",
        is_published=True,
    )
    TranslationService().upsert_product_translation(
        tenant_id=tenant.id,
        product=product,
        locale="en",
        name="English Only",
    )
    headers = {"X-Tenant-ID": tenant.slug}
    blocked = client.get(
        "/api/v1/store/products/base-prod?locale=en",
        headers=headers,
    )
    assert blocked.get_json()["product"]["name"] == "Base"

    FeatureFlagService().set_tenant_override(
        tenant_id=tenant.id, code="multi_language", value=True
    )
    enabled = client.get(
        "/api/v1/store/products/base-prod?locale=en",
        headers=headers,
    )
    assert enabled.get_json()["product"]["name"] == "English Only"
