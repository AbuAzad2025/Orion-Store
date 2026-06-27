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
    detail = client.get(f"/api/v1/returns/{rid}", headers=store_headers)
    assert detail.status_code == 200
    listed = client.get("/api/v1/returns/", headers=headers)
    assert listed.status_code == 200
    approved = client.put(f"/api/v1/returns/{rid}/approve", headers=headers)
    assert approved.status_code == 200
    completed = client.post(f"/api/v1/returns/{rid}/complete", headers=headers)
    assert completed.status_code == 200


def test_b2b_api_full_flow(client, app):
    tenant, headers = _setup_admin(client, app)
    product = ProductService().create(
        tenant_id=tenant.id,
        name="B2B API",
        slug="b2b-api",
        price="80.00",
        quantity=10,
        is_published=True,
    )
    pl = client.post(
        "/api/v1/b2b/price-lists",
        headers=headers,
        json={"name": "Dealer Prices"},
    )
    assert pl.status_code == 201
    groups = client.get("/api/v1/b2b/customer-groups", headers=headers)
    assert groups.status_code == 200
    list_id = pl.get_json()["price_list"]["id"]
    item = client.post(
        f"/api/v1/b2b/price-lists/{list_id}/items",
        headers=headers,
        json={"product_id": product.id, "price": "70.00"},
    )
    assert item.status_code == 201
    group = client.post(
        "/api/v1/b2b/customer-groups",
        headers=headers,
        json={
            "name": "Dealers",
            "code": "dealers",
            "discount_percent": "5",
            "price_list_id": list_id,
        },
    )
    assert group.status_code == 201
    quote = client.post(
        "/api/v1/b2b/quotes",
        headers=headers,
        json={"customer_group_id": group.get_json()["group"]["id"]},
    )
    assert quote.status_code == 201
    qid = quote.get_json()["quote"]["id"]
    qitem = client.post(
        f"/api/v1/b2b/quotes/{qid}/items",
        headers=headers,
        json={"product_id": product.id, "quantity": 2},
    )
    assert qitem.status_code == 201
    detail = client.get(f"/api/v1/b2b/quotes/{qid}", headers=headers)
    assert detail.status_code == 200
    converted = client.post(
        f"/api/v1/b2b/quotes/{qid}/convert",
        headers=headers,
        json={"customer_email": "dealer@test.com"},
    )
    assert converted.status_code == 201


def test_oms_api_full_flow(client, app):
    tenant, headers = _setup_admin(client, app)
    product = ProductService().create(
        tenant_id=tenant.id,
        name="OMS API",
        slug="oms-api",
        price="25.00",
        quantity=10,
        is_published=True,
    )
    created = client.post(
        "/api/v1/oms/warehouses",
        headers=headers,
        json={"name": "Central", "code": "central", "is_default": True},
    )
    assert created.status_code == 201
    wh_id = created.get_json()["warehouse"]["id"]
    listed = client.get("/api/v1/oms/warehouses", headers=headers)
    assert listed.status_code == 200
    inv = client.put(
        "/api/v1/oms/inventory",
        headers=headers,
        json={
            "warehouse_id": wh_id,
            "product_id": product.id,
            "quantity": 20,
        },
    )
    assert inv.status_code == 200
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="oms@test.com",
        shipping_address={"city": "TLV"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    fulfillment = client.post(
        "/api/v1/oms/fulfillments",
        headers=headers,
        json={"order_public_id": str(order.public_id), "warehouse_id": wh_id},
    )
    assert fulfillment.status_code == 201
    fid = fulfillment.get_json()["fulfillment"]["id"]
    shipped = client.post(
        f"/api/v1/oms/fulfillments/{fid}/ship",
        headers=headers,
        json={"tracking_number": "OMS-TRACK-1"},
    )
    assert shipped.status_code == 200
