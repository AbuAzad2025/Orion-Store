"""Wave 9 RMA/B2B/OMS API tests."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def _setup_admin(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="W9 API", slug="w9-api", email="w9@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@w9.com",
        password="password123",
        is_admin=True,
    )
    return tenant, auth_headers(admin, tenant_id=tenant.slug)


def test_returns_api_flow(client, app):
    tenant, headers = _setup_admin(client, app)
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Ret API",
        slug="ret-api",
        price="30.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="api@test.com",
        shipping_address={"city": "Jenin"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    store_headers = tenant_headers(tenant.slug)
    reasons = client.get("/api/v1/returns/reasons", headers=store_headers)
    assert reasons.status_code == 200

    from order.order import OrderItem

    oi = OrderItem.query.filter_by(order_id=order.id).first()
    created = client.post(
        "/api/v1/returns/",
        headers=store_headers,
        json={
            "order_public_id": str(order.public_id),
            "items": [{"order_item_id": oi.id, "quantity": 1}],
            "reason_code": "defective",
        },
    )
    assert created.status_code == 201
    rid = created.get_json()["return"]["id"]
    approved = client.put(f"/api/v1/returns/{rid}/approve", headers=headers)
    assert approved.status_code == 200


def test_b2b_api_quote(client, app):
    tenant, headers = _setup_admin(client, app)
    ProductService().create(
        tenant_id=tenant.id,
        name="B2B API",
        slug="b2b-api",
        price="80.00",
        quantity=10,
        is_published=True,
    )
    group = client.post(
        "/api/v1/b2b/customer-groups",
        headers=headers,
        json={"name": "Dealers", "code": "dealers", "discount_percent": "5"},
    )
    assert group.status_code == 201
    quote = client.post(
        "/api/v1/b2b/quotes",
        headers=headers,
        json={"customer_group_id": group.get_json()["group"]["id"]},
    )
    assert quote.status_code == 201


def test_oms_api_warehouse(client, app):
    tenant, headers = _setup_admin(client, app)
    created = client.post(
        "/api/v1/oms/warehouses",
        headers=headers,
        json={"name": "Central", "code": "central", "is_default": True},
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/oms/warehouses", headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()["warehouses"]) >= 1
