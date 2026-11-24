"""Store-admin menu organization and the admin UI fixes behind it."""

from __future__ import annotations

from auth.auth_service import AuthService
from support.http import auth_headers, tenant_headers
from tenant_svc.tenant_service import TenantService


def _store_admin(app, slug: str) -> dict[str, str]:
    from orion.extensions import db

    from tenant.tenant import Tenant
    from user.user import User

    with app.app_context():
        tenant = Tenant.query.filter_by(slug=slug).first()
        if tenant is None:
            tenant = TenantService().create_tenant(
                name="Menu UI", slug=slug, email=f"{slug}@test.com"
            )
        admin = User.query.filter_by(
            tenant_id=tenant.id, is_admin=True, is_superuser=False, deleted_at=None
        ).first()
        if admin is None:
            admin = AuthService().register_tenant_user(
                tenant_id=tenant.id,
                email=f"admin@{slug}.test",
                password="password123",
                is_admin=True,
            )
        return auth_headers(admin, app=app, tenant_id=slug)


def test_store_admin_sidebar_is_grouped(client, app):
    headers = auth_headers(
        AuthService().register_tenant_user(
            tenant_id=TenantService().create_tenant(
                name="Menu Groups", slug="menu-groups", email="mg@test.com"
            ).id,
            email="admin@mg.test",
            password="password123",
            is_admin=True,
        ),
        app=app,
        tenant_id="menu-groups",
    )
    resp = client.get("/admin/store/dashboard", headers=headers)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for label in (
        "الرئيسية",
        "الطلبات والتنفيذ",
        "المالية والفوترة",
        "التسويق والمحتوى",
        "الإعدادات والتكاملات",
        "أدوات المطوّر",
    ):
        assert label in html, label
    # All previous links are still present, just reorganized.
    for path in (
        "/admin/store/products",
        "/admin/store/gateways",
        "/admin/store/reconciliation",
        "/admin/store/ui-kit",
        "/admin/store/oms",
    ):
        assert path in html, path
    # Currency is platform-only; it must not appear in the store-admin menu.
    assert "/admin/store/currency" not in html
    assert 'href="/admin/platform/currency"' not in html


def test_platform_currency_page_is_reachable(client, platform_admin_headers):
    resp = client.get(
        "/admin/platform/currency", headers={**platform_admin_headers, "Host": "orion.azadexa.com"}
    )
    assert resp.status_code == 200
    assert b"currency-rate-form" in resp.data


def test_rectify_action_endpoint_exists(client, app):
    headers = _store_admin(app, "rectify-ui")
    # Creating a rectification request and actioning it must both be possible.
    created = client.post(
        "/api/v1/compliance/data-requests",
        headers=headers,
        json={"customer_email": "buyer@rectify.test", "request_type": "rectify"},
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    rid = created.get_json()["data_request"]["id"]
    action = client.post(
        f"/api/v1/compliance/data-requests/{rid}/rectify", headers=headers
    )
    assert action.status_code == 200, action.get_data(as_text=True)
    assert action.get_json()["request"]["status"] == "completed"


def test_oms_product_picker_api(client, app):
    from catalog_svc.product_service import ProductService

    headers = _store_admin(app, "oms-picker")
    with app.app_context():
        from tenant.tenant import Tenant

        tenant = Tenant.query.filter_by(slug="oms-picker").first()
        ProductService().create(
            tenant_id=tenant.id, name="Picker", slug="picker", price="9.99", quantity=1
        )
    resp = client.get("/api/v1/oms/products", headers=headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    products = resp.get_json()["products"]
    assert any(p["name"] == "Picker" and isinstance(p["id"], int) for p in products)
