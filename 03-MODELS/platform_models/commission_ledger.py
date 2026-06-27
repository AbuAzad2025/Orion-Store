"""Commission ledger (§4.49, wave 4 #38)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class PlatformCommissionLedger(db.Model):
    __tablename__ = "platform_commission_ledger"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    financial_event_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_events.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), default="credit")
    entry_type: Mapped[str] = mapped_column(String(30), default="commission")
    payment_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
