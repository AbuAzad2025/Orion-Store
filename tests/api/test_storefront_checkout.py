"""Storefront cart and checkout flow (wave 3)."""

from __future__ import annotations

import pytest
from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store_with_product(app):
    tenants = TenantService()
    products = ProductService()
    tenant = tenants.create_tenant(
        name="Checkout Store", slug="checkout-store", email="co@test.com"
    )
    product = products.create(
        tenant_id=tenant.id,
        name="Buyable",
        slug="buyable",
        price="15.00",
        quantity=5,
        is_published=True,
    )
    return tenant, product


def test_cart_checkout_flow(client, store_with_product):
    tenant, product = store_with_product
    headers = tenant_headers(tenant.slug)

    cart_resp = client.post("/api/v1/store/cart", headers=headers)
    assert cart_resp.status_code == 201
    token = cart_resp.get_json()["cart"]["cart_token"]

    add = client.post(
        f"/api/v1/store/cart/{token}/items",
        headers=headers,
        json={"product_id": product.id, "quantity": 2},
    )
    assert add.status_code == 201

    checkout = client.post(
        "/api/v1/store/checkout",
        headers=headers,
        json={
            "cart_token": token,
            "customer_email": "buyer@example.com",
            "shipping_address": {"city": "Ramallah"},
        },
    )
    assert checkout.status_code == 201
    order = checkout.get_json()["order"]
    assert order["payment_status"] == "pending"
    assert order["total"] == "30.00"

    public_id = order["public_id"]
    get_order = client.get(f"/api/v1/store/orders/{public_id}", headers=headers)
    assert get_order.status_code == 200
