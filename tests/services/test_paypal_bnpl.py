"""PayPal and BNPL integration unit tests (wave 8)."""

from __future__ import annotations

import pytest

from bnpl_svc.bnpl_service import BnplService
from core.exceptions import NotFoundError, ValidationError
from integrations.payments.bnpl import charge_bnpl
from integrations.payments.paypal import charge_paypal
from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def test_paypal_sandbox_charge(app):
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="paypal",
        display_name="PayPal",
        is_enabled=True,
        is_sandbox=True,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-PP-1",
        customer_email="t@test.com",
        shipping_address={},
        subtotal="50",
        total="50",
    )
    order.id = 42
    result = charge_paypal(order=order, gateway=gateway, amount="50.00")
    assert result["success"] is True
    assert result["provider_payment_id"].startswith("pp_test_")


def test_paypal_missing_credentials(app):
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="paypal",
        display_name="PayPal",
        is_enabled=True,
        is_sandbox=False,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-PP-2",
        customer_email="t@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    order.id = 43
    result = charge_paypal(order=order, gateway=gateway, amount="10.00")
    assert result["success"] is False


def test_upsert_paypal_gateway(app):
    tenant = TenantService().create_tenant(
        name="PayPal GW", slug="paypal-gw", email="pgw@test.com"
    )
    gw = GatewayService().upsert_paypal(
        tenant_id=tenant.id,
        client_id="client",
        client_secret="secret",
        is_sandbox=True,
    )
    assert gw.provider == "paypal"
    assert gw.is_enabled is True
    assert gw.credentials_encrypted


def test_bnpl_upsert_and_charge(app):
    tenant = TenantService().create_tenant(
        name="BNPL Co", slug="bnpl-co", email="bnpl@test.com"
    )
    svc = BnplService()
    row = svc.upsert_provider(
        tenant_id=tenant.id,
        provider="tabby",
        merchant_id="m-123",
        api_key="key-abc",
        is_enabled=True,
    )
    assert row.is_enabled is True
    order = Order(
        tenant_id=tenant.id,
        order_number="ORD-BNPL",
        customer_email="b@test.com",
        shipping_address={},
        subtotal="100",
        total="100",
    )
    order.id = 77
    result = charge_bnpl(order=order, provider_row=row, amount="100.00")
    assert result["success"] is True
    assert "external_transaction_id" in result


def test_bnpl_get_enabled_missing(app):
    tenant = TenantService().create_tenant(
        name="BNPL Off", slug="bnpl-off", email="boff@test.com"
    )
    with pytest.raises(NotFoundError):
        BnplService().get_enabled(tenant.id, "tamara")


def test_bnpl_invalid_provider(app):
    tenant = TenantService().create_tenant(
        name="BNPL Bad", slug="bnpl-bad", email="bbad@test.com"
    )
    with pytest.raises(ValidationError):
        BnplService().upsert_provider(
            tenant_id=tenant.id, provider="klarna", is_enabled=True
        )


def test_list_enabled_checkout_methods(app):
    tenant = TenantService().create_tenant(
        name="Pay Methods", slug="pay-methods", email="pm@test.com"
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    methods = GatewayService().list_enabled_for_checkout(tenant.id)
    codes = [m["code"] for m in methods]
    assert "cod" in codes
