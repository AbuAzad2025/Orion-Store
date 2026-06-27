"""Gateway and stripe integration tests (wave 4)."""

from __future__ import annotations

import pytest

from core.exceptions import NotFoundError
from integrations.payments.stripe_connect import charge_stripe
from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway
from platform_svc.reconciliation_service import ReconciliationService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def test_ensure_cod_and_list_gateways(app):
    tenant = TenantService().create_tenant(
        name="GW", slug="gw-store", email="gw@test.com"
    )
    svc = GatewayService()
    cod = svc.ensure_cod_gateway(tenant.id)
    assert cod.provider == "cod"
    assert len(svc.list_for_tenant(tenant.id)) == 1


def test_get_enabled_gateway_missing(app):
    tenant = TenantService().create_tenant(
        name="GW2", slug="gw2-store", email="gw2@test.com"
    )
    with pytest.raises(NotFoundError):
        GatewayService().get_enabled(tenant.id, "stripe")


def test_stripe_sandbox_charge(app):
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="stripe",
        display_name="Stripe",
        is_enabled=True,
        is_sandbox=True,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-1-TEST",
        customer_email="t@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    order.id = 99
    result = charge_stripe(order=order, gateway=gateway, amount="10.00")
    assert result["success"] is True


def test_get_enabled_stripe_gateway(app):
    tenant = TenantService().create_tenant(
        name="Stripe GW", slug="stripe-gw", email="sgw@test.com"
    )
    from orion.extensions import db

    gw = TenantPaymentGateway(
        tenant_id=tenant.id,
        provider="stripe",
        display_name="Stripe",
        is_enabled=True,
        is_sandbox=True,
        status="active",
    )
    db.session.add(gw)
    db.session.commit()
    found = GatewayService().get_enabled(tenant.id, "stripe")
    assert found.provider == "stripe"


def test_stripe_live_charge_with_credentials(app):
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="stripe",
        display_name="Stripe",
        is_enabled=True,
        is_sandbox=False,
        credentials_encrypted="enc",
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-1-LIVE",
        customer_email="t@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    order.id = 100
    result = charge_stripe(order=order, gateway=gateway, amount="10.00")
    assert result["success"] is True


def test_stripe_missing_credentials(app):
    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="stripe",
        display_name="Stripe",
        is_enabled=True,
        is_sandbox=False,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-1-FAIL",
        customer_email="t@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    order.id = 101
    result = charge_stripe(order=order, gateway=gateway, amount="10.00")
    assert result["success"] is False


def test_reconciliation_settles_pending(app):
    from decimal import Decimal

    from orion.extensions import db
    from platform_models.commission_ledger import PlatformCommissionLedger
    from platform_svc.financial_events_service import FinancialEventsService
    from platform_svc.platform_settings_service import PlatformSettingsService

    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Rec", slug="rec-store", email="rec@test.com"
    )
    event = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="10.00",
        event_type="order.payment",
        source_entity="order",
        source_id=1,
    )
    entry = PlatformCommissionLedger(
        tenant_id=tenant.id,
        financial_event_id=event.id,
        gross_amount=Decimal("10"),
        commission_percent=Decimal("0.01"),
        commission_amount=Decimal("0.10"),
        status="pending",
    )
    db.session.add(entry)
    db.session.commit()
    count = ReconciliationService().settle_pending_commissions()
    assert count == 1
