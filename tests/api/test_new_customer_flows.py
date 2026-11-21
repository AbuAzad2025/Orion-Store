"""Coverage for the customer self-service and storefront helper modules."""

from __future__ import annotations

import pytest
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    tenant = TenantService().create_tenant(
        name="Flow Store", slug="flow-store", email="flow@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Flow Product",
        slug="flow-product",
        price="20.00",
        quantity=10,
        is_published=True,
    )
    auth = AuthService()
    customer = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="buyer@flow.com",
        password="password123",
        is_admin=False,
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@flow.com",
        password="password123",
        is_admin=True,
    )
    return tenant, product, customer, admin


def _plan(app, tenant_id):
    from subscription_svc.subscription_service import SubscriptionService

    return SubscriptionService().create_plan(
        tenant_id=tenant_id,
        name="Gold",
        code="gold",
        billing_period_days=30,
        price="9.99",
    )


def test_customer_service_flows(client, store):
    tenant, product, customer, _admin = store
    headers = auth_headers(customer, tenant_id=tenant.slug)
    _plan(client.app, tenant.id)

    plans = client.get("/api/v1/store/account/plans", headers=headers)
    assert plans.status_code == 200
    assert plans.get_json()["plans"]

    sub = client.post(
        "/api/v1/store/account/subscribe",
        headers=headers,
        json={"plan_id": plans.get_json()["plans"][0]["id"]},
    )
    assert sub.status_code == 201

    credit = client.get("/api/v1/store/account/credit", headers=headers)
    assert credit.status_code == 200
    assert "balance" in credit.get_json()["credit"]

    quote = client.post(
        "/api/v1/store/account/quote-requests",
        headers=headers,
        json={"product_id": product.id, "quantity": 2, "notes": "bulk"},
    )
    assert quote.status_code == 201
    assert (
        client.get("/api/v1/store/account/quote-requests", headers=headers).status_code
        == 200
    )

    registry = client.post(
        "/api/v1/store/account/gift-registries",
        headers=headers,
        json={"registry_name": "Wedding", "event_type": "wedding"},
    )
    assert registry.status_code == 201
    slug = registry.get_json()["registry"]["slug"]
    assert (
        client.get("/api/v1/store/account/gift-registries", headers=headers).status_code
        == 200
    )
    item = client.post(
        f"/api/v1/store/account/gift-registries/{slug}/items",
        headers=headers,
        json={"product_id": product.id},
    )
    assert item.status_code == 201


def test_logout_revokes_tokens(client, store):
    tenant, _product, customer, _admin = store
    headers = auth_headers(customer, tenant_id=tenant.slug)
    assert client.get("/api/v1/store/account/me", headers=headers).status_code == 200
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/v1/store/account/me", headers=headers).status_code == 401


def test_brands_and_pickup_locations(client, store):
    tenant, _product, _customer, admin = store
    admin_headers = auth_headers(admin, tenant_id=tenant.slug)
    created = client.post(
        "/api/v1/brands/", headers=admin_headers, json={"name": "Local Brand"}
    )
    assert created.status_code == 201
    assert client.get("/api/v1/brands/", headers=admin_headers).status_code == 200

    from bopis_svc.bopis_service import BopisService

    BopisService().create_location(
        tenant_id=tenant.id, code="main", name="Main", address={"text": "Center"}
    )
    locations = client.get(
        "/api/v1/store/pickup-locations", headers=tenant_headers(tenant.slug)
    )
    assert locations.status_code == 200
    assert locations.get_json()["locations"]


def test_anonymous_order_payload_has_no_pii(client, store):
    tenant, product, _customer, _admin = store
    from order_svc.cart_service import CartService
    from order_svc.checkout_service import CheckoutService

    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="private@flow.com",
        shipping_address={"city": "Ramallah"},
    )
    response = client.get(
        f"/api/v1/store/orders/{order.public_id}", headers=tenant_headers(tenant.slug)
    )
    assert response.status_code == 200
    payload = response.get_json()["order"]
    assert "customer_email" not in payload
    assert "shipping_address" not in payload
