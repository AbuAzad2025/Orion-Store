"""Storefront HTML i18n — `lang`/`dir` follow the request locale."""

from __future__ import annotations

import re

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from scripts.audit_a11y import _audit_html_tag
from tenant_svc.tenant_service import TenantService

from support.http import tenant_headers

_HTML_TAG_RE = re.compile(r"<html\b[^>]*>", re.I)
_HTML_ATTR_RE = re.compile(r"""\b(lang|dir)\s*=\s*["']([^"']*)["']""", re.I)

STOREFRONT_PATHS = (
    "/",
    "/product/widget",
    "/category/widgets",
    "/cart",
    "/checkout",
    "/account",
)


def _html_attrs(response) -> dict[str, str]:
    match = _HTML_TAG_RE.search(response.get_data(as_text=True))
    assert match, "response is missing an <html> tag"
    return {key.lower(): value for key, value in _HTML_ATTR_RE.findall(match.group(0))}


def _make_storefront(*, multi_language: bool = True):
    tenant = TenantService().create_tenant(
        name="I18n Store", slug="i18n-store", email="i18n@test.com"
    )
    if multi_language:
        # `multi_language` defaults to False; the query-string locale is only
        # honoured for tenants that opt in (same path as the storefront API).
        FeatureFlagService().set_tenant_override(
            tenant_id=tenant.id, code="multi_language", value=True
        )
    CategoryService().create(tenant_id=tenant.id, name="Widgets", slug="widgets")
    ProductService().create(
        tenant_id=tenant.id,
        name="Widget",
        slug="widget",
        price="9.99",
        quantity=3,
        is_published=True,
    )
    return tenant_headers(tenant.slug)


def test_storefront_defaults_to_arabic_rtl(client, app) -> None:
    headers = _make_storefront(multi_language=False)
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    attrs = _html_attrs(response)
    assert attrs["lang"] == "ar"
    assert attrs["dir"] == "rtl"


def test_locale_query_switches_to_english_ltr(client, app) -> None:
    headers = _make_storefront()
    english = client.get("/?locale=en", headers=headers)
    assert english.status_code == 200
    attrs = _html_attrs(english)
    assert attrs["lang"] == "en"
    assert attrs["dir"] == "ltr"

    # Same page without the query string stays Arabic — no static leakage.
    default = client.get("/", headers=headers)
    assert _html_attrs(default)["lang"] == "ar"


def test_every_storefront_route_passes_locale(client, app) -> None:
    headers = _make_storefront()
    for path in STOREFRONT_PATHS:
        separator = "&" if "?" in path else "?"
        response = client.get(f"{path}{separator}locale=en", headers=headers)
        assert response.status_code == 200, path
        attrs = _html_attrs(response)
        assert attrs["lang"] == "en", path
        assert attrs["dir"] == "ltr", path


def test_existing_page_smoke_is_not_broken(client, app) -> None:
    headers = _make_storefront(multi_language=False)
    for path in STOREFRONT_PATHS:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, path
        attrs = _html_attrs(response)
        assert attrs == {"lang": "ar", "dir": "rtl"}, path


def test_a11y_audit_matches_direction_to_language() -> None:
    accepted = (
        '<html lang="ar" dir="rtl">',
        '<html lang="he" dir="rtl">',
        '<html lang="en" dir="ltr">',
        '<html lang="fr" dir="ltr">',
        # Dynamic form used by base.html — validated for every probe locale.
        '<html lang="{{ locale|default(\'ar\') }}" '
        "dir=\"{{ 'rtl' if locale[:2]|lower in ['ar','he'] else 'ltr' }}\">",
    )
    for tag in accepted:
        issues: list[str] = []
        _audit_html_tag(tag, "t.html", issues)
        assert issues == [], (tag, issues)

    rejected = (
        '<html lang="ar" dir="ltr">',
        '<html lang="en" dir="rtl">',
        '<html lang="{{ locale }}" dir="rtl">',
    )
    for tag in rejected:
        issues = []
        _audit_html_tag(tag, "t.html", issues)
        assert issues, tag
