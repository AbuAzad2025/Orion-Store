"""Nightly reconciliation (wave 4 #48) + platform API support."""

from __future__ import annotations

from core.utils import utc_now
from orion.extensions import db
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent
from tenant.tenant import Tenant


class ReconciliationService:
    def settle_pending_commissions(self, tenant_id: int | None = None) -> int:
        """Settle pending commissions *only* for confirmed financial events.

        When ``tenant_id`` is supplied the match is strictly tenant-scoped: both
        the ledger row and its financial event must belong to that tenant. This
        is the guard used by the nightly job (one tenant at a time) so a
        settlement can never cross tenant boundaries.
        """
        query = PlatformCommissionLedger.query.join(
            FinancialEvent,
            PlatformCommissionLedger.financial_event_id == FinancialEvent.id,
        ).filter(
            PlatformCommissionLedger.status == "pending",
            FinancialEvent.status == "completed",
        )
        if tenant_id is not None:
            query = query.filter(
                PlatformCommissionLedger.tenant_id == tenant_id,
                FinancialEvent.tenant_id == tenant_id,
            )
        pending = query.all()
        for entry in pending:
            entry.status = "settled"
            entry.notes = (
                entry.notes or ""
            ) + f" matched tenant={entry.tenant_id} at {utc_now().isoformat()}"
        if pending:
            db.session.commit()
        return len(pending)

    def get_status(self, tenant_id: int | None = None) -> dict:
        ledger = PlatformCommissionLedger.query
        events = FinancialEvent.query
        if tenant_id is not None:
            ledger = ledger.filter_by(tenant_id=tenant_id)
            events = events.filter_by(tenant_id=tenant_id)
        return {
            "pending_commission_entries": ledger.filter_by(status="pending").count(),
            "settled_commission_entries": ledger.filter_by(status="settled").count(),
            "financial_events_total": events.count(),
        }

    def tenant_ids(self) -> list[int]:
        """Active tenants to reconcile, enumerated in platform-admin context."""
        return [
            row.id for row in Tenant.query.filter(Tenant.deleted_at.is_(None)).all()
        ]

    def run(self) -> dict:
        """Reconcile tenant by tenant and record the per-tenant match result."""
        tenant_ids = self.tenant_ids()
        results: list[dict] = []
        for tenant_id in tenant_ids:
            matched = self.settle_pending_commissions(tenant_id=tenant_id)
            results.append(
                {
                    "tenant_id": tenant_id,
                    "matched_commission_entries": matched,
                    "status": self.get_status(tenant_id=tenant_id),
                }
            )
        return {
            "settled_commission_entries": sum(
                item["matched_commission_entries"] for item in results
            ),
            "tenants_processed": len(tenant_ids),
            "tenants": results,
            **self.get_status(),
        }
