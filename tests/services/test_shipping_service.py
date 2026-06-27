"""Shipping service unit tests (wave 6)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.exceptions import NotFoundError
from shipping_svc.shipping_service import ShippingService
from tenant_svc.tenant_service import TenantService


def test_seed_and_calculate_flat_rate(app):
    tenants = TenantService()
    shipping = ShippingService()
    tenant = tenants.create_tenant(
        name="Ship Co", slug="ship-co", email="ship@test.com"
    )
    method = shipping.seed_flat_rate(tenant.id, cost="12.50")
    cost = shipping.calculate_cost(
        tenant_id=tenant.id,
        method_code=method.code,
        subtotal=Decimal("50.00"),
        shipping_address={"city": "haifa"},
    )
    assert cost == Decimal("12.50")


def test_free_shipping_threshold(app):
    tenants = TenantService()
    shipping = ShippingService()
    tenant = tenants.create_tenant(
        name="Free Ship", slug="free-ship", email="free@test.com"
    )
    method = shipping.seed_flat_rate(tenant.id, cost="15.00")
    cost = shipping.calculate_cost(
        tenant_id=tenant.id,
        method_code=method.code,
        subtotal=Decimal("150.00"),
        shipping_address={},
    )
    assert cost == Decimal("0")


def test_unknown_method_raises(app):
    tenants = TenantService()
    shipping = ShippingService()
    tenant = tenants.create_tenant(
        name="No Ship", slug="no-ship", email="noship@test.com"
    )
    with pytest.raises(NotFoundError):
        shipping.calculate_cost(
            tenant_id=tenant.id,
            method_code="missing",
            subtotal=Decimal("10"),
            shipping_address={},
        )
