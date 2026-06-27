"""Commission service tests (wave 4)."""

from __future__ import annotations

from decimal import Decimal

from platform_svc.commission_service import CommissionService
from platform_svc.financial_events_service import FinancialEventsService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_commission_apply_from_event(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Comm", slug="comm-store", email="comm@test.com"
    )
    event = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="50.00",
        event_type="order.payment",
        source_entity="order",
        source_id=1,
    )
    ledger = CommissionService().apply_from_event(event, order_id=1)
    assert ledger is not None
    assert ledger.commission_amount == Decimal("0.50")
    assert event.commission_ledger_id == ledger.id
