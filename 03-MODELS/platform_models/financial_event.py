"""Financial events — central ledger (§4.49, wave 4 #34)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class FinancialEvent(db.Model):
    __tablename__ = "financial_events"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    source_entity: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[int] = mapped_column(PrimaryKeyType, nullable=False)
    gateway_id: Mapped[int | None] = mapped_column(PrimaryKeyType, nullable=True)
    platform_gateway_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, nullable=True
    )
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", db.JSON, default=dict)
    commission_applied: Mapped[bool] = mapped_column(Boolean, default=True)
    commission_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    commission_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    commission_ledger_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "public_id": str(self.public_id),
            "direction": self.direction,
            "event_type": self.event_type,
            "amount": str(self.amount),
            "currency": self.currency,
            "commission_amount": (
                str(self.commission_amount) if self.commission_amount else None
            ),
            "status": self.status,
        }
