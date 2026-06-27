"""Payment model (§4.7, wave 4 #37)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class Payment(db.Model, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    financial_event_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType,
        ForeignKey("financial_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ILS")
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_dict(self) -> dict:
        return {
            "public_id": str(self.public_id),
            "amount": str(self.amount),
            "currency": self.currency,
            "payment_method": self.payment_method,
            "status": self.status,
            "order_id": self.order_id,
        }
