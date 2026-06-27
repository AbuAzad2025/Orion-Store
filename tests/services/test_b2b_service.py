"""B2B service unit tests (wave 9)."""

from __future__ import annotations

from b2b_svc.b2b_service import B2bService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def test_b2b_quote_to_order(app):
    tenant = TenantService().create_tenant(
        name="B2B Co", slug="b2b-co", email="b2b@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Wholesale",
        slug="wholesale",
        price="100.00",
        quantity=20,
        is_published=True,
    )
    svc = B2bService()
    group = svc.create_customer_group(
        tenant_id=tenant.id,
        name="Wholesale",
        code="wholesale",
        discount_percent="10",
        is_wholesale=True,
    )
    quote = svc.create_quote(tenant_id=tenant.id, customer_group_id=group.id)
    svc.add_quote_item(
        tenant_id=tenant.id,
        quote_id=quote.id,
        product_id=product.id,
        quantity=2,
    )
    order = svc.convert_quote_to_order(
        tenant_id=tenant.id,
        quote_id=quote.id,
        customer_email="buyer@b2b.com",
    )
    assert order.total > 0
    assert order.customer_email == "buyer@b2b.com"


def test_b2b_price_list(app):
    tenant = TenantService().create_tenant(
        name="PL Co", slug="pl-co", email="pl@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="PL Prod",
        slug="pl-prod",
        price="50.00",
        quantity=5,
        is_published=True,
    )
    svc = B2bService()
    pl = svc.create_price_list(tenant_id=tenant.id, name="VIP")
    svc.add_price_item(
        tenant_id=tenant.id,
        price_list_id=pl.id,
        product_id=product.id,
        price="40.00",
    )
    group = svc.create_customer_group(
        tenant_id=tenant.id,
        name="VIP",
        code="vip",
        price_list_id=pl.id,
    )
    price = svc.resolve_unit_price(
        tenant_id=tenant.id,
        product_id=product.id,
        quantity=1,
        customer_group_id=group.id,
    )
    from decimal import Decimal

    assert price == Decimal("40.00")
