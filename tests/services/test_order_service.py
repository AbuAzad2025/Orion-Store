"""Order service unit tests (wave 3 coverage)."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from order_svc.order_service import OrderService
from tenant_svc.tenant_service import TenantService


def _checkout_order(app):
    tenants = TenantService()
    products = ProductService()
    carts = CartService()
    checkout = CheckoutService()
    tenant = tenants.create_tenant(name="Ord", slug="ord-store", email="o@test.com")
    product = products.create(
        tenant_id=tenant.id,
        name="Goods",
        slug="goods",
        price="10.00",
        quantity=3,
        is_published=True,
    )
    cart = carts.get_or_create_cart(tenant_id=tenant.id)
    carts.add_item(cart=cart, product_id=product.id, quantity=1)
    order = checkout.checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Nablus"},
    )
    return tenant, order


def test_list_for_tenant(app):
    tenant, order = _checkout_order(app)
    orders = OrderService().list_for_tenant(tenant.id)
    assert len(orders) == 1
    assert orders[0].id == order.id


def test_get_by_public_id_not_found(app):
    tenant, _ = _checkout_order(app)
    with pytest.raises(NotFoundError):
        OrderService().get_by_public_id(
            tenant.id, "00000000-0000-0000-0000-000000000099"
        )
