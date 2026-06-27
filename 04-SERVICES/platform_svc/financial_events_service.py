"""Financial events service — all money flows here (wave 4 #35)."""

from __future__ import annotations

from decimal import Decimal

from core.constants import COMMISSION_FALLBACK_CHAIN
from core.utils import utc_now
from orion.extensions import db
from platform_models.financial_event import FinancialEvent
from platform_models.platform_settings import PlatformSettings
from tenant.tenant import Tenant


class FinancialEventsService:
    def resolve_commission_percent(self, tenant_id: int) -> Decimal:
        tenant = Tenant.query.get(tenant_id)
        if tenant and tenant.platform_commission_percent is not None:
            return Decimal(str(tenant.platform_commission_percent))
        settings = PlatformSettings.query.filter_by(singleton="1").first()
        if settings:
            return Decimal(str(settings.default_commission_percent))
        return Decimal(str(COMMISSION_FALLBACK_CHAIN[-1]))

    def record_inbound(
        self,
        *,
        tenant_id: int,
        amount: Decimal | str,
        event_type: str,
        source_entity: str,
        source_id: int,
        currency: str = "ILS",
        description: str | None = None,
        apply_commission: bool = True,
    ) -> FinancialEvent:
        value = Decimal(str(amount))
        if value <= 0:
            raise ValueError("amount must be positive")
        percent = (
            self.resolve_commission_percent(tenant_id) if apply_commission else None
        )
        commission_amount = (
            (value * percent).quantize(Decimal("0.01")) if percent is not None else None
        )
        event = FinancialEvent(
            tenant_id=tenant_id,
            direction="inbound",
            event_type=event_type,
            amount=value,
            currency=currency,
            source_entity=source_entity,
            source_id=source_id,
            description=description,
            commission_applied=apply_commission,
            commission_percent=percent,
            commission_amount=commission_amount,
            status="completed",
            completed_at=utc_now(),
        )
        db.session.add(event)
        db.session.commit()
        return event
