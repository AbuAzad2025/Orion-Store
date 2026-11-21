"""CMS pages: admin CRUD → public localized view → soft-delete hiding."""

from __future__ import annotations

from auth.auth_service import AuthService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from i18n_svc.page_service import PageService
from support.http import auth_headers, tenant_headers
from tenant_svc.tenant_service import TenantService


def _make_tenant(app, slug: str, *, with_admin: bool = True):
    tenant = TenantService().create_tenant(
        name=f"CMS {slug}", slug=slug, email=f"{slug}@test.com"
    )
    # Query-string locale is honoured only for opted-in tenants.
    FeatureFlagService().set_tenant_override(
        tenant_id=tenant.id, code="multi_language", value=True
    )
    if not with_admin:
        return tenant, None
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email=f"admin@{slug}.test",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def _html(response) -> str:
    return response.get_data(as_text=True)


def test_cms_page_create_localized_view_update_soft_delete(client, app) -> None:
    tenant, admin = _make_tenant(app, "cms-flow")
    admin_headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    public_headers = tenant_headers(tenant.slug)

    created = client.post(
        "/api/v1/i18n/pages",
        headers=admin_headers,
        json={"slug": "about", "title": "من نحن", "is_published": True},
    )
    assert created.status_code == 201, _html(created)
    page_id = created.get_json()["page"]["id"]

    arabic = client.put(
        f"/api/v1/i18n/pages/{page_id}/translations/ar",
        headers=admin_headers,
        json={"title": "من نحن", "body": "محتوى عربي للصفحة", "slug": "about"},
    )
    english = client.put(
        f"/api/v1/i18n/pages/{page_id}/translations/en",
        headers=admin_headers,
        json={"title": "About Us", "body": "English page body", "slug": "about"},
    )
    assert arabic.status_code == 200, _html(arabic)
    assert english.status_code == 200, _html(english)

    ar_view = client.get("/pages/about", headers=public_headers)
    assert ar_view.status_code == 200
    ar_html = _html(ar_view)
    assert "محتوى عربي للصفحة" in ar_html
    assert '<html lang="ar" dir="rtl">' in ar_html
    assert "<h1 " in ar_html

    en_view = client.get("/pages/about?locale=en", headers=public_headers)
    assert en_view.status_code == 200
    en_html = _html(en_view)
    assert "English page body" in en_html
    assert 'lang="en"' in en_html
    assert 'dir="ltr"' in en_html
    assert "محتوى عربي للصفحة" not in en_html

    updated = client.put(
        f"/api/v1/i18n/pages/{page_id}",
        headers=admin_headers,
        json={"title": "عن المتجر", "is_published": True},
    )
    assert updated.status_code == 200
    assert updated.get_json()["page"]["title"] == "عن المتجر"

    en_edit = client.put(
        f"/api/v1/i18n/pages/{page_id}/translations/en",
        headers=admin_headers,
        json={"title": "Our Store", "body": "Updated English body"},
    )
    assert en_edit.status_code == 200
    assert "Updated English body" in _html(
        client.get("/pages/about?locale=en", headers=public_headers)
    )

    deleted = client.delete(f"/api/v1/i18n/pages/{page_id}", headers=admin_headers)
    assert deleted.status_code == 200
    missing = client.get("/pages/about", headers=public_headers)
    assert missing.status_code == 404
    assert "404" in _html(missing)  # themed, not a bare error string
    listed = client.get("/api/v1/i18n/pages", headers=public_headers)
    assert listed.get_json()["pages"] == []


def test_cms_page_footer_policy_links_follow_publication(client, app) -> None:
    tenant, admin = _make_tenant(app, "cms-footer")
    admin_headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    public_headers = tenant_headers(tenant.slug)

    privacy = client.post(
        "/api/v1/i18n/pages",
        headers=admin_headers,
        json={"slug": "privacy-policy", "title": "سياسة الخصوصية", "is_published": True},
    )
    client.post(
        "/api/v1/i18n/pages",
        headers=admin_headers,
        json={"slug": "terms", "title": "الشروط والأحكام", "is_published": True},
    )
    assert privacy.status_code == 201

    home = _html(client.get("/", headers=public_headers))
    assert 'href="/pages/privacy-policy"' in home
    assert 'href="/pages/terms"' in home

    privacy_id = privacy.get_json()["page"]["id"]
    client.put(
        f"/api/v1/i18n/pages/{privacy_id}",
        headers=admin_headers,
        json={"is_published": False},
    )
    home = _html(client.get("/", headers=public_headers))
    assert 'href="/pages/privacy-policy"' not in home
    assert 'href="/pages/terms"' in home


def test_cms_page_mutations_require_tenant_admin(client, app) -> None:
    tenant, _ = _make_tenant(app, "cms-rbac", with_admin=False)
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="customer@cms-rbac.test",
        password="password123",
        is_admin=False,
    )
    headers = auth_headers(customer, app=app, tenant_id=tenant.slug)

    assert client.post(
        "/api/v1/i18n/pages", headers=headers, json={"slug": "x", "title": "X"}
    ).status_code == 403
    assert client.get("/api/v1/i18n/pages?all=1", headers=headers).status_code == 403


def test_cms_page_admin_ui_route(client, app) -> None:
    tenant, admin = _make_tenant(app, "cms-admin-ui")
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    response = client.get("/admin/store/pages", headers=headers)
    assert response.status_code == 200
    body = _html(response)
    assert 'id="pages-list"' in body
    assert "admin_pages.js" in body


def test_page_service_duplicate_slug_and_soft_delete(app) -> None:
    tenant, _ = _make_tenant(app, "cms-service", with_admin=False)
    service = PageService()
    page = service.create_page(
        tenant_id=tenant.id, slug="faq", title="FAQ", is_published=True
    )
    try:
        service.create_page(tenant_id=tenant.id, slug="faq", title="Duplicate")
    except Exception as exc:
        assert exc.__class__.__name__ == "ConflictError"
    else:
        raise AssertionError("duplicate slug must be rejected")

    service.delete_page(page)
    assert service.list_published(tenant.id) == []
    assert len(service.list_all(tenant.id)) == 1
