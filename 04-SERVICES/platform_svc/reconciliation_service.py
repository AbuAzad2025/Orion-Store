"""Nightly reconciliation (wave 4 #48) + platform API support."""

from __future__ import annotations

from core.utils import utc_now
from orion.extensions import db
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent


class ReconciliationService:
    def settle_pending_commissions(self) -> int:
        pending = PlatformCommissionLedger.query.filter_by(status="pending").all()
        for entry in pending:
            entry.status = "settled"
            entry.notes = (entry.notes or "") + f" settled {utc_now().isoformat()}"
        db.session.commit()
        return len(pending)

    def get_status(self) -> dict:
        pending = PlatformCommissionLedger.query.filter_by(status="pending").count()
        settled = PlatformCommissionLedger.query.filter_by(status="settled").count()
        events = FinancialEvent.query.count()
        return {
            "pending_commission_entries": pending,
            "settled_commission_entries": settled,
            "financial_events_total": events,
        }

    def run(self) -> dict:
        settled = self.settle_pending_commissions()
        return {"settled_commission_entries": settled, **self.get_status()}
