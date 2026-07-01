from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class StoreCredit(db.Model, TimestampMixin):
    __tablename__ = "store_credits"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_email", name="uq_store_credit_email"),
    )

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ILS", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "balance": str(self.balance),
            "currency": self.currency,
            "is_active": self.is_active,
        }


class StoreCreditTransaction(db.Model):
    __tablename__ = "store_credit_transactions"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    credit_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("store_credits.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "credit_id": self.credit_id,
            "transaction_type": self.transaction_type,
            "amount": str(self.amount),
            "balance_after": str(self.balance_after),
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
        }
