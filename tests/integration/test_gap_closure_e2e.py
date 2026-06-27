"""Gap closure — refund, PDF invoice, events, pagination, E2E."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order.order import Order
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.document_renderer import DocumentRenderer
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_storefront_e2e_browse_cart_checkout_pay_invoice(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="E2E Store", slug="e2e-store", email="e2e@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="E2E Product",
        slug="e2e-product",
        price="30.00",
        quantity=5,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)

    for path in ("/", "/product/e2e-product", "/cart", "/checkout", "/account"):
        page = client.get(path, headers=headers)
        assert page.status_code == 200

    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="e2e@buyer.com",
        shipping_address={"city": "Haifa"},
    )
    pay = client.post(
        f"/api/v1/store/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "cod"},
    )
    assert pay.status_code == 200
    body = pay.get_json()
    assert body["invoice"]["pdf_artifact_path"]
    assert body["invoice"]["has_rendered_html"] is True

    inv = client.get(f"/api/v1/store/orders/{order.public_id}/invoice", headers=headers)
    assert inv.status_code == 200
    assert "azadexa-platform-footer" in inv.get_json()["rendered_html"]

    order_row = Order.query.filter_by(id=order.id).first()
    assert order_row.fulfillment_status == "paid_pending_fulfillment"


def test_refund_flow(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Refund Store", slug="refund-store", email="ref@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@ref.com",
        password="password123",
        is_admin=True,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Refundable",
        slug="refundable",
        price="15.00",
        quantity=2,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@ref.com",
        shipping_address={"city": "Jaffa"},
    )
    paid = PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    payment_id = paid["payment"]["public_id"]
    headers = auth_headers(admin, tenant_id=tenant.slug)
    refund = client.post(
        f"/api/v1/payments/{payment_id}/refund",
        headers=headers,
        json={"reason": "customer request"},
    )
    assert refund.status_code == 200
    order_row = Order.query.filter_by(id=order.id).first()
    assert order_row.payment_status == "refunded"


def test_pagination_on_product_list(client, app):
    tenant = TenantService().create_tenant(
        name="Page Store", slug="page-store", email="page@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@page.com",
        password="password123",
        is_admin=True,
    )
    for i in range(3):
        ProductService().create(
            tenant_id=tenant.id,
            name=f"P{i}",
            slug=f"p-{i}",
            price="1.00",
            quantity=1,
            is_published=True,
        )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    resp = client.get("/api/v1/products/?page=1&per_page=2", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["products"]) == 2
    assert body["pagination"]["total"] == 3


def test_document_renderer_validation(app):
    renderer = DocumentRenderer()
    try:
        renderer.validate_template("<div>no footer</div>")
        raised = False
    except Exception:
        raised = True
    assert raised
    footer = (
        '<div></div><footer id="azadexa-platform-footer" '
        'data-immutable="true"></footer>'
    )
    renderer.validate_template(footer)


def test_reconciliation_api(client, platform_admin_headers):
    status = client.get(
        "/api/v1/platform/reconciliation", headers=platform_admin_headers
    )
    assert status.status_code == 200
    run = client.post(
        "/api/v1/platform/reconciliation/run", headers=platform_admin_headers
    )
    assert run.status_code == 200


def test_admin_login_page(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert b"login-form" in resp.data
