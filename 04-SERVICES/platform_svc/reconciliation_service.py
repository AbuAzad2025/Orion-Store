"""Nightly reconciliation stub (wave 4 #48)."""

from __future__ import annotations

from core.utils import utc_now
from orion.extensions import db
from platform_models.commission_ledger import PlatformCommissionLedger


class ReconciliationService:
    def settle_pending_commissions(self) -> int:
        pending = PlatformCommissionLedger.query.filter_by(status="pending").all()
        for entry in pending:
            entry.status = "settled"
            entry.notes = (entry.notes or "") + f" settled {utc_now().isoformat()}"
        db.session.commit()
        return len(pending)
