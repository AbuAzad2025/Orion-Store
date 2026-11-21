"""Tax calculation based on the shipping address (jurisdiction matching)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from order.order import Order
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from tax_svc.tax_service import TaxService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant(app):
    return TenantService().create_tenant(
        name="Tax By Address", slug="tax-by-address", email="tax-address@test.com"
    )


def _seed_jurisdiction(
    tenant_id, *, code, rate, country_code="US", region=None, priority=0
):
    svc = TaxService()
    jur = svc.create_jurisdiction(
        tenant_id=tenant_id,
        code=code,
        name=code,
        country_code=country_code,
        region=region,
    )
    svc.set_rate(
        tenant_id=tenant_id, jurisdiction_id=jur.id, rate=rate, priority=priority
    )
    return jur


def test_address_matching_jurisdiction_returns_tax(tenant):
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.0725", region="CA")

    tax = TaxService().compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "region": "CA"},
    )
    assert tax == Decimal("7.25")


def test_address_without_matching_jurisdiction_returns_zero(tenant):
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.0725", region="CA")

    tax = TaxService().compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "PS", "region": "Ramallah"},
    )
    assert tax == Decimal("0")


def test_no_jurisdictions_returns_zero(tenant):
    tax = TaxService().compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "region": "CA", "city": "LA"},
    )
    assert tax == Decimal("0")


def test_more_specific_jurisdiction_wins(tenant):
    _seed_jurisdiction(tenant.id, code="US", rate="0.05")
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.0725", region="CA")

    svc = TaxService()
    assert svc.compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "region": "CA"},
    ) == Decimal("7.25")
    # A country-level jurisdiction still applies to other regions.
    assert svc.compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "region": "NY"},
    ) == Decimal("5.00")


def test_shipping_is_taxable_when_provided(tenant):
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.10", region="CA")

    tax = TaxService().compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "region": "CA"},
        shipping_cost=Decimal("20.00"),
    )
    assert tax == Decimal("12.00")


def test_checkout_uses_address_based_tax(tenant):
    PlatformSettingsService().ensure_seeded()
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.10", region="CA")
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Taxed Item",
        slug="taxed-item",
        price="50.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)

    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@tax.test",
        shipping_address={"country_code": "US", "region": "CA"},
    )
    assert order.tax_amount == Decimal("5.00")
    assert Order.query.filter_by(id=order.id).first().tax_amount == Decimal("5.00")


def test_tax_calculate_api_preview(client, tenant):
    _seed_jurisdiction(tenant.id, code="US-CA", rate="0.0725", region="CA")
    headers = tenant_headers(tenant.slug)

    res = client.post(
        "/api/v1/tax/calculate",
        headers=headers,
        json={
            "subtotal": "100.00",
            "shipping_address": {"country_code": "US", "region": "CA"},
        },
    )
    assert res.status_code == 200
    assert res.get_json()["tax_amount"] == "7.25"

    no_match = client.post(
        "/api/v1/tax/calculate",
        headers=headers,
        json={
            "subtotal": "100.00",
            "shipping_address": {"country_code": "PS", "region": "Gaza"},
        },
    )
    assert no_match.status_code == 200
    assert no_match.get_json()["tax_amount"] == "0.00"
