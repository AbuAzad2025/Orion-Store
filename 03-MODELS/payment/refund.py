"""Refund model (wave 4 #37)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class Refund(db.Model, TimestampMixin):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    financial_event_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
