from __future__ import annotations

import uuid
from decimal import Decimal

from reconciliation.reconciliation_v2 import (
    FinancialReconciliationItem,
    FinancialReconciliationRun,
)

from core.exceptions import NotFoundError
from orion.extensions import db


class ReconciliationV2Service:
    def create_run(self, *, tenant_id: int) -> FinancialReconciliationRun:
        run = FinancialReconciliationRun(
            tenant_id=tenant_id, run_number=f"REC-{uuid.uuid4().hex[:8].upper()}"
        )
        db.session.add(run)
        db.session.commit()
        return run

    def add_item(
        self,
        *,
        tenant_id: int,
        run_id: int,
        financial_event_id: int,
        expected_amount: str | Decimal,
        actual_amount: str | Decimal,
    ) -> FinancialReconciliationItem:
        run = FinancialReconciliationRun.query.filter_by(
            id=run_id, tenant_id=tenant_id
        ).first()
        if not run:
            raise NotFoundError("Reconciliation run not found.")
        item = FinancialReconciliationItem(
            tenant_id=tenant_id,
            run_id=run_id,
            financial_event_id=financial_event_id,
            expected_amount=Decimal(str(expected_amount)),
            actual_amount=Decimal(str(actual_amount)),
        )
        db.session.add(item)
        db.session.commit()
        return item

    def complete_run(
        self, *, run_id: int, tenant_id: int
    ) -> FinancialReconciliationRun:
        run = FinancialReconciliationRun.query.filter_by(
            id=run_id, tenant_id=tenant_id
        ).first()
        if not run:
            raise NotFoundError("Run not found.")
        items = FinancialReconciliationItem.query.filter_by(run_id=run.id).all()
        run.total_events = len(items)
        run.matched_count = sum(
            1 for i in items if i.expected_amount == i.actual_amount
        )
        run.discrepancy_count = run.total_events - run.matched_count
        run.status = "completed"
        from datetime import datetime, timezone

        run.completed_at = datetime.now(timezone.utc).isoformat()
        db.session.commit()
        return run

    def list_runs(self, tenant_id: int) -> list[FinancialReconciliationRun]:
        return (
            FinancialReconciliationRun.query.filter_by(tenant_id=tenant_id)
            .order_by(FinancialReconciliationRun.created_at.desc())
            .all()
        )
