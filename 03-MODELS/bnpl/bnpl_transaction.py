"""BNPL transaction linked to orders (§4.23, wave 8 #62)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class BnplTransaction(db.Model, TimestampMixin):
    __tablename__ = "bnpl_transactions"
    __table_args__ = (
        UniqueConstraint(
            "external_transaction_id", name="uq_bnpl_transactions_external"
        ),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    external_transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    installment_plan: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "provider": self.provider,
            "external_transaction_id": self.external_transaction_id,
            "status": self.status,
            "amount": str(self.amount),
            "installment_plan": self.installment_plan,
        }
