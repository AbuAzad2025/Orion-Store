"""Store contact number and WhatsApp ordering buttons remain optional."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def test_tenant_admin_sets_contact_number(client, app):
    tenant = TenantService().create_tenant(
        name="WA Store", slug="wa-store", email="wa@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="wa-admin@test.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)

    invalid = client.put(
        "/api/v1/tenant/contact", headers=headers, json={"phone": "123"}
    )
    assert invalid.status_code == 400

    saved = client.put(
        "/api/v1/tenant/contact",
        headers=headers,
        json={"phone": "+970 50 123 4567"},
    )
    assert saved.status_code == 200
    assert saved.get_json()["phone"] == "+970 50 123 4567"

    fetched = client.get("/api/v1/tenant/contact", headers=headers)
    assert fetched.status_code == 200
    assert fetched.get_json()["phone"] == "+970 50 123 4567"


def test_customer_cannot_change_contact_number(client, app):
    tenant = TenantService().create_tenant(
        name="WA Store 2", slug="wa-store-2", email="wa2@test.com"
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="wa-customer@test.com",
        password="password123",
        is_admin=False,
    )
    response = client.put(
        "/api/v1/tenant/contact",
        headers=auth_headers(customer, tenant_id=tenant.slug),
        json={"phone": "+970501234567"},
    )
    assert response.status_code in (401, 403)


def test_whole_cart_can_be_sent_to_whatsapp(client, app):
    tenant = TenantService().create_tenant(
        name="WA Cart Store", slug="wa-cart-store", email="wacart@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Cart Product",
        slug="cart-product",
        price="15.00",
        quantity=10,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)
    cart = client.post("/api/v1/store/cart", headers=headers).get_json()["cart"]
    token = cart["cart_token"]
    client.post(
        f"/api/v1/store/cart/{token}/items",
        headers=headers,
        json={"product_id": product.id, "quantity": 2},
    )

    from orion.extensions import db
    from tenant.tenant import Tenant

    with app.app_context():
        row = db.session.get(Tenant, tenant.id)
        row.phone = "+970501234567"
        db.session.commit()

    response = client.post(
        f"/api/v1/store/cart/{token}/whatsapp-message",
        headers=headers,
        json={"customer_name": "أحمد", "notes": "بدون بصل"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "Cart Product" in data["message"]
    assert "2 × 15.00 = 30.00" in data["message"]
    assert "الإجمالي: 30.00 ₪" in data["message"]
    assert "بدون بصل" in data["message"]
    assert data["url"].startswith("https://wa.me/970501234567?text=")


def test_whatsapp_message_rejects_empty_cart_and_missing_number(client, app):
    tenant = TenantService().create_tenant(
        name="WA Empty", slug="wa-empty", email="waempty@test.com"
    )
    headers = tenant_headers(tenant.slug)
    token = client.post("/api/v1/store/cart", headers=headers).get_json()["cart"][
        "cart_token"
    ]

    missing_number = client.post(
        f"/api/v1/store/cart/{token}/whatsapp-message", headers=headers, json={}
    )
    assert missing_number.status_code == 400

    from orion.extensions import db
    from tenant.tenant import Tenant

    with app.app_context():
        row = db.session.get(Tenant, tenant.id)
        row.phone = "+970501234567"
        db.session.commit()

    empty_cart = client.post(
        f"/api/v1/store/cart/{token}/whatsapp-message", headers=headers, json={}
    )
    assert empty_cart.status_code == 400


def test_storefront_shows_whatsapp_buttons_when_number_configured(client, app):
    tenant = TenantService().create_tenant(
        name="WA Store 3", slug="wa-store-3", email="wa3@test.com"
    )
    ProductService().create(
        tenant_id=tenant.id,
        name="WA Product",
        slug="wa-product",
        price="15.00",
        quantity=3,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)

    before = client.get("/", headers=headers)
    assert before.status_code == 200
    assert "wa.me/" not in before.get_data(as_text=True)

    from orion.extensions import db
    from tenant.tenant import Tenant

    with app.app_context():
        row = db.session.get(Tenant, tenant.id)
        row.phone = "+970501234567"
        db.session.commit()

    after = client.get("/", headers=headers)
    html = after.get_data(as_text=True)
    assert "wa.me/970501234567" in html
    assert "اطلب عبر واتساب" in html

    product_page = client.get("/product/wa-product", headers=headers)
    assert "wa.me/970501234567" in product_page.get_data(as_text=True)
