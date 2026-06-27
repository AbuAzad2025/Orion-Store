"""I18n service unit tests (wave 7)."""

from __future__ import annotations

from i18n_svc.i18n_service import I18nService

from tenant_svc.tenant_service import TenantService


def test_ensure_locales_seeded(app):
    i18n = I18nService()
    i18n.ensure_locales_seeded()
    locales = i18n.list_active_locales()
    codes = {loc.code for loc in locales}
    assert "ar" in codes
    assert "en" in codes


def test_resolve_locale_fallback(app):
    tenants = TenantService()
    tenant = tenants.create_tenant(
        name="Locale Co", slug="locale-co", email="loc@test.com"
    )
    i18n = I18nService()
    i18n.ensure_locales_seeded()
    assert i18n.resolve_locale(tenant, requested="xx") in ("ar", "en")
