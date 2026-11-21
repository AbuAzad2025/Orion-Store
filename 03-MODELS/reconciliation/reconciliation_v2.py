from __future__ import annotations

from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class FinancialReconciliationRun(db.Model, TimestampMixin):
    __tablename__ = "financial_reconciliation_runs"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discrepancy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_number": self.run_number,
            "status": self.status,
            "total_events": self.total_events,
            "matched_count": self.matched_count,
            "discrepancy_count": self.discrepancy_count,
        }


class FinancialReconciliationItem(db.Model):
    __tablename__ = "financial_reconciliation_items"
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_reconciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    financial_event_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "financial_event_id": self.financial_event_id,
            "expected_amount": str(self.expected_amount),
            "actual_amount": str(self.actual_amount),
            "status": self.status,
        }
