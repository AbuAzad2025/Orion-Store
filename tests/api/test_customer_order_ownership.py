"""Customer order history is tied to the account, with legacy email fallback."""

from __future__ import annotations

import pytest
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    tenant = TenantService().create_tenant(
        name="Ownership Store", slug="ownership-store", email="owner@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Ownership Product",
        slug="ownership-product",
        price="12.00",
        quantity=50,
        is_published=True,
    )
    auth = AuthService()
    customer_a = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="customer-a@test.com",
        password="password123",
        is_admin=False,
    )
    customer_b = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="customer-b@test.com",
        password="password123",
        is_admin=False,
    )
    return tenant, product, customer_a, customer_b


def _checkout(client, headers, product, email):
    cart = client.post("/api/v1/store/cart", headers=headers)
    assert cart.status_code == 201
    token = cart.get_json()["cart"]["cart_token"]
    added = client.post(
        f"/api/v1/store/cart/{token}/items",
        headers=headers,
        json={"product_id": product.id, "quantity": 1},
    )
    assert added.status_code == 201
    response = client.post(
        "/api/v1/store/checkout",
        headers=headers,
        json={
            "cart_token": token,
            "customer_email": email,
            "shipping_address": {"city": "Ramallah"},
        },
    )
    assert response.status_code == 201
    return response.get_json()["order"]


def test_registered_customer_order_is_linked_to_account(client, store):
    tenant, product, customer_a, customer_b = store
    headers_a = auth_headers(customer_a, tenant_id=tenant.slug)
    headers_b = auth_headers(customer_b, tenant_id=tenant.slug)

    order = _checkout(client, headers_a, product, "customer-a@test.com")
    assert order["user_id"] == customer_a.id
    assert order["is_guest"] is False

    orders_a = client.get("/api/v1/store/account/orders", headers=headers_a)
    assert orders_a.status_code == 200
    ids_a = [row["public_id"] for row in orders_a.get_json()["orders"]]
    assert order["public_id"] in ids_a

    orders_b = client.get("/api/v1/store/account/orders", headers=headers_b)
    assert orders_b.status_code == 200
    ids_b = [row["public_id"] for row in orders_b.get_json()["orders"]]
    assert order["public_id"] not in ids_b


def test_guest_order_is_not_visible_to_other_customers(client, store):
    tenant, product, _customer_a, customer_b = store
    guest_order = _checkout(
        client, tenant_headers(tenant.slug), product, "guest@test.com"
    )
    assert guest_order["user_id"] is None
    assert guest_order["is_guest"] is True

    orders_b = client.get(
        "/api/v1/store/account/orders",
        headers=auth_headers(customer_b, tenant_id=tenant.slug),
    )
    ids_b = [row["public_id"] for row in orders_b.get_json()["orders"]]
    assert guest_order["public_id"] not in ids_b


def test_legacy_order_matched_by_email_is_still_visible(client, store):
    tenant, product, customer_a, _customer_b = store
    legacy = _checkout(
        client, tenant_headers(tenant.slug), product, "customer-a@test.com"
    )
    assert legacy["user_id"] is None

    orders_a = client.get(
        "/api/v1/store/account/orders",
        headers=auth_headers(customer_a, tenant_id=tenant.slug),
    )
    ids_a = [row["public_id"] for row in orders_a.get_json()["orders"]]
    assert legacy["public_id"] in ids_a
