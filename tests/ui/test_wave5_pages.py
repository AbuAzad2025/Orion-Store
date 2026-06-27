"""Wave 5 HTML UI smoke tests."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def test_storefront_pages(client, app):
    tenant = TenantService().create_tenant(
        name="UI Store", slug="ui-store", email="ui@test.com"
    )
    ProductService().create(
        tenant_id=tenant.id,
        name="Widget",
        slug="widget",
        price="9.99",
        quantity=3,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)

    for path in ("/", "/product/widget", "/cart", "/checkout", "/account"):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 200
        assert b"Azadexa" in resp.data or tenant.name.encode() in resp.data


def test_tenant_admin_pages(client, app):
    tenant = TenantService().create_tenant(
        name="Admin UI", slug="admin-ui", email="aui@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@aui.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)

    for path in (
        "/admin/store/dashboard",
        "/admin/store/gateways",
        "/admin/store/documents",
        "/admin/store/feature-flags",
        "/admin/store/returns",
        "/admin/store/b2b",
        "/admin/store/oms",
    ):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 200
        assert b"api_client.js" in resp.data


def test_platform_admin_pages(client, app, platform_admin_headers):
    tenant = TenantService().create_tenant(
        name="Plat UI", slug="plat-ui", email="plat@test.com"
    )
    dash = client.get("/admin/platform/dashboard", headers=platform_admin_headers)
    assert dash.status_code == 200

    finance = client.get(
        f"/admin/platform/stores/{tenant.id}/finance",
        headers=platform_admin_headers,
    )
    assert finance.status_code == 200
    assert b"financial-report" in finance.data
