"""Wave 15 launch gap closure tests."""

from __future__ import annotations

from i18n_svc.glossary_service import GlossaryService
from i18n_svc.page_service import PageService
from support.http import tenant_headers

from core.audit_log import audit_log
from integrations.payments.palpay import charge_palpay
from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway
from tenant_svc.tenant_service import TenantService


def test_palpay_sandbox_charge():
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="palpay",
        display_name="PalPay",
        is_enabled=True,
        is_sandbox=True,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-PP",
        customer_email="t@test.com",
        shipping_address={},
        total="10",
    )
    order.id = 7
    result = charge_palpay(order=order, gateway=gateway, amount="10.00")
    assert result["success"] is True


def test_cms_page_and_glossary_flow(app):
    tenant = TenantService().create_tenant(
        name="Pages", slug="pages-store", email="pages@test.com"
    )
    page = PageService().create_page(
        tenant_id=tenant.id, slug="about", title="About", is_published=True
    )
    merged = PageService().merge_translation(page, "ar")
    assert merged["slug"] == "about"
    term = GlossaryService().upsert_term(
        tenant_id=tenant.id,
        source_locale="ar",
        target_locale="en",
        source_term="متجر",
        target_term="store",
    )
    assert term.target_term == "store"


def test_store_account_register_and_orders(client, app):
    tenant = TenantService().create_tenant(
        name="Acct", slug="acct-store", email="acct@test.com"
    )
    headers = tenant_headers(tenant.slug)
    reg = client.post(
        "/api/v1/store/account/register",
        json={
            "email": "buyer@acct.com",
            "password": "password123",
            "first_name": "Buyer",
        },
        headers=headers,
    )
    assert reg.status_code == 201
    token = reg.get_json()["access_token"]
    auth = {**headers, "Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/store/account/me", headers=auth)
    assert me.status_code == 200
    orders = client.get("/api/v1/store/account/orders", headers=auth)
    assert orders.status_code == 200


def test_audit_log_persists(app):
    with app.app_context():
        row = audit_log(
            action="test.action",
            resource_type="test",
            resource_id="1",
            tenant_id=None,
        )
        assert row.id


def test_i18n_pages_api(client, app):
    tenant = TenantService().create_tenant(
        name="Pg API", slug="pg-api", email="pg@test.com"
    )
    PageService().create_page(
        tenant_id=tenant.id, slug="terms", title="Terms", is_published=True
    )
    headers = tenant_headers(tenant.slug)
    resp = client.get("/api/v1/i18n/pages/terms", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["page"]["slug"] == "terms"
    listed = client.get("/api/v1/i18n/pages", headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()["pages"]) == 1


def test_i18n_glossary_api(client, app):
    from auth.auth_service import AuthService

    tenant = TenantService().create_tenant(
        name="Glos", slug="glos-store", email="glos@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@glos.com",
        password="password123",
        is_admin=True,
    )
    from support.http import auth_headers

    headers = auth_headers(admin, tenant_id=tenant.slug)
    created = client.post(
        "/api/v1/i18n/glossary",
        json={
            "source_locale": "ar",
            "target_locale": "en",
            "source_term": "سلة",
            "target_term": "cart",
        },
        headers=headers,
    )
    assert created.status_code == 201
    listed = client.get(
        "/api/v1/i18n/glossary?source=ar&target=en",
        headers=tenant_headers(tenant.slug),
    )
    assert listed.status_code == 200
    assert len(listed.get_json()["terms"]) == 1


def test_store_account_login_rejects_admin(client, app):
    from auth.auth_service import AuthService

    tenant = TenantService().create_tenant(
        name="Adm", slug="adm-store", email="adm@test.com"
    )
    AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@adm.com",
        password="password123",
        is_admin=True,
    )
    resp = client.post(
        "/api/v1/store/account/login",
        json={"email": "admin@adm.com", "password": "password123"},
        headers=tenant_headers(tenant.slug),
    )
    assert resp.status_code == 403
