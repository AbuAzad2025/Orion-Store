"""Per-tenant warehouse stock stays aligned with the storefront catalogue."""

from __future__ import annotations

from catalog_svc.product_service import ProductService
from oms.warehouse import InventoryLevel
from oms_svc.oms_service import OmsService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from tenant_svc.tenant_service import TenantService


def _stock(app, tenant_id, product_id) -> int | None:
    with app.app_context():
        level = InventoryLevel.query.filter_by(
            tenant_id=tenant_id, product_id=product_id
        ).first()
        return level.quantity if level else None


def test_product_quantity_and_warehouse_are_synced(app):
    tenant = TenantService().create_tenant(
        name="Stock Store", slug="stock-store", email="stock@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Stocked",
        slug="stocked",
        price="10.00",
        quantity=12,
        is_published=True,
    )
    with app.app_context():
        warehouse = OmsService().get_default_warehouse(tenant.id)
        assert warehouse.code == "main"
    assert _stock(app, tenant.id, product.id) == 12

    ProductService().update(product, quantity=20)
    assert _stock(app, tenant.id, product.id) == 20

    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=3)
    CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )
    assert _stock(app, tenant.id, product.id) == 17
