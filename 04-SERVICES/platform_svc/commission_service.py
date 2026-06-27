"""Commission ledger service (wave 4 #39)."""

from __future__ import annotations

from decimal import Decimal

from orion.extensions import db
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent


class CommissionService:
    def apply_from_event(
        self,
        event: FinancialEvent,
        *,
        payment_id: int | None = None,
        order_id: int | None = None,
    ) -> PlatformCommissionLedger | None:
        if not event.commission_applied or not event.commission_amount:
            return None
        existing = PlatformCommissionLedger.query.filter_by(
            financial_event_id=event.id
        ).first()
        if existing:
            return existing
        entry = PlatformCommissionLedger(
            tenant_id=event.tenant_id,
            financial_event_id=event.id,
            payment_id=payment_id,
            order_id=order_id,
            gross_amount=event.amount,
            commission_percent=event.commission_percent or Decimal("0"),
            commission_amount=event.commission_amount,
            currency=event.currency,
            status="pending",
        )
        db.session.add(entry)
        db.session.flush()
        event.commission_ledger_id = entry.id
        db.session.commit()
        return entry
