"""Per-store financial report for platform admin (wave 5 #54)."""

from __future__ import annotations

from decimal import Decimal

from core.exceptions import NotFoundError
from order.order import Order
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent
from platform_models.invoice import Invoice
from tenant.tenant import Tenant


class StoreFinancialReportService:
    def build(self, tenant_id: int) -> dict:
        tenant = Tenant.query.filter_by(id=tenant_id).first()
        if not tenant:
            raise NotFoundError("Tenant not found.")

        events = (
            FinancialEvent.query.filter_by(tenant_id=tenant_id)
            .order_by(FinancialEvent.created_at.desc())
            .limit(20)
            .all()
        )
        inbound = FinancialEvent.query.filter_by(
            tenant_id=tenant_id, direction="inbound"
        ).all()
        total_gross = sum((e.amount for e in inbound), Decimal("0"))
        total_commission = sum(
            (e.commission_amount or Decimal("0") for e in inbound), Decimal("0")
        )
        ledger_pending = PlatformCommissionLedger.query.filter_by(
            tenant_id=tenant_id, status="pending"
        ).count()
        orders_paid = Order.query.filter_by(
            tenant_id=tenant_id, payment_status="paid"
        ).count()
        invoice_count = Invoice.query.filter_by(tenant_id=tenant_id).count()

        return {
            "tenant": tenant.to_dict(),
            "summary": {
                "total_inbound": str(total_gross),
                "total_commission": str(total_commission),
                "orders_paid": orders_paid,
                "invoices_issued": invoice_count,
                "pending_commission_entries": ledger_pending,
            },
            "recent_events": [e.to_dict() for e in events],
        }
