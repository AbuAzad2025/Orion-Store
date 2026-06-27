"""Cart service unit tests (wave 3 coverage)."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError, ValidationError
from order_svc.cart_service import CartService
from tenant_svc.tenant_service import TenantService


def test_get_or_create_reuses_active_cart(app):
    tenants = TenantService()
    carts = CartService()
    products = ProductService()
    tenant = tenants.create_tenant(name="Cart", slug="cart-store", email="c@test.com")
    product = products.create(
        tenant_id=tenant.id,
        name="Item",
        slug="item",
        price="5.00",
        quantity=10,
        is_published=True,
    )
    cart1 = carts.get_or_create_cart(tenant_id=tenant.id)
    carts.add_item(cart=cart1, product_id=product.id, quantity=1)
    cart2 = carts.get_or_create_cart(tenant_id=tenant.id, cart_token=cart1.cart_token)
    assert cart2.id == cart1.id
    assert len(carts.list_items(cart2)) == 1


def test_get_cart_not_found(app):
    tenants = TenantService()
    tenant = tenants.create_tenant(name="Missing", slug="missing-cart", email="m@c.com")
    with pytest.raises(NotFoundError):
        CartService().get_cart(tenant.id, "nonexistent-token")


def test_add_item_invalid_quantity(app):
    tenants = TenantService()
    products = ProductService()
    carts = CartService()
    tenant = tenants.create_tenant(name="Qty", slug="qty-store", email="q@c.com")
    product = products.create(
        tenant_id=tenant.id,
        name="P",
        slug="p",
        price="1.00",
        quantity=5,
        is_published=True,
    )
    cart = carts.get_or_create_cart(tenant_id=tenant.id)
    with pytest.raises(ValidationError):
        carts.add_item(cart=cart, product_id=product.id, quantity=0)
