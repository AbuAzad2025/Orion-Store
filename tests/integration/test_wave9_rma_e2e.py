"""Wave 9 RMA complete with refund E2E."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def test_rma_complete_refund_flow(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="RMA E2E", slug="rma-e2e", email="re2e@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@re2e.com",
        password="password123",
        is_admin=True,
    )
    admin_headers = auth_headers(admin, tenant_id=tenant.slug)
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Refund Me",
        slug="refund-me",
        price="40.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="e2e@test.com",
        shipping_address={"city": "Haifa"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    oi = OrderItem.query.filter_by(order_id=order.id).first()
    store_headers = tenant_headers(tenant.slug)
    created = client.post(
        "/api/v1/returns/",
        headers=store_headers,
        json={
            "order_public_id": str(order.public_id),
            "items": [{"order_item_id": oi.id, "quantity": 1, "restock": True}],
        },
    )
    rid = created.get_json()["return"]["id"]
    client.put(f"/api/v1/returns/{rid}/approve", headers=admin_headers)
    done = client.post(f"/api/v1/returns/{rid}/complete", headers=admin_headers)
    assert done.status_code == 200
    body = done.get_json()
    assert body["return"]["status"] == "refunded"
    assert body["refund"] is not None
