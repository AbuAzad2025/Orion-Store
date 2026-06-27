"""Voucher service unit tests (wave 6)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from discount_svc.voucher_service import VoucherService

from core.exceptions import NotFoundError, ValidationError
from tenant_svc.tenant_service import TenantService


def test_percentage_voucher_discount(app):
    tenants = TenantService()
    vouchers = VoucherService()
    tenant = tenants.create_tenant(
        name="Voucher Co", slug="voucher-co", email="v@test.com"
    )
    vouchers.create(
        tenant_id=tenant.id,
        code="save10",
        name="10% off",
        type="percentage",
        value="10",
    )
    preview = vouchers.validate(tenant.id, "SAVE10", Decimal("100.00"))
    assert preview.discount_amount == Decimal("10.00")


def test_fixed_voucher_capped_by_subtotal(app):
    tenants = TenantService()
    vouchers = VoucherService()
    tenant = tenants.create_tenant(name="Fixed Co", slug="fixed-co", email="f@test.com")
    vouchers.create(
        tenant_id=tenant.id,
        code="five",
        name="$5 off",
        type="fixed_amount",
        value="5",
    )
    preview = vouchers.validate(tenant.id, "FIVE", Decimal("3.00"))
    assert preview.discount_amount == Decimal("3.00")


def test_min_order_validation(app):
    tenants = TenantService()
    vouchers = VoucherService()
    tenant = tenants.create_tenant(name="Min Co", slug="min-co", email="m@test.com")
    vouchers.create(
        tenant_id=tenant.id,
        code="big",
        name="Big order",
        type="percentage",
        value="5",
        min_order_value="50",
    )
    with pytest.raises(ValidationError):
        vouchers.validate(tenant.id, "BIG", Decimal("20"))


def test_unknown_voucher_raises(app):
    tenants = TenantService()
    vouchers = VoucherService()
    tenant = tenants.create_tenant(
        name="Missing", slug="missing-v", email="mv@test.com"
    )
    with pytest.raises(NotFoundError):
        vouchers.validate(tenant.id, "NOPE", Decimal("10"))
