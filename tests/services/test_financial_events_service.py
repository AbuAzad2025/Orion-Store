"""Financial events service tests (wave 4)."""

from __future__ import annotations

from decimal import Decimal

from platform_svc.financial_events_service import FinancialEventsService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_record_inbound_applies_platform_commission(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Fin Store", slug="fin-store", email="fin@test.com"
    )
    svc = FinancialEventsService()
    event = svc.record_inbound(
        tenant_id=tenant.id,
        amount="100.00",
        event_type="order.payment",
        source_entity="order",
        source_id=1,
    )
    assert event.direction == "inbound"
    assert event.commission_percent == Decimal("0.0100")
    assert event.commission_amount == Decimal("1.00")
    assert svc.resolve_commission_percent(tenant.id) == Decimal("0.0100")
