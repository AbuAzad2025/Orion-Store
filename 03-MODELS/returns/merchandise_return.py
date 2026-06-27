"""RMA return request models (§4.16, wave 9 #63)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class MerchandiseReturn(db.Model, TimestampMixin):
    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    return_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="requested", nullable=False)
    return_type: Mapped[str] = mapped_column(
        String(20), default="refund", nullable=False
    )
    reason_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType,
        ForeignKey("return_reasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    refund_method: Mapped[str] = mapped_column(
        String(20), default="original_payment", nullable=False
    )
    approved_by: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "return_number": self.return_number,
            "order_id": self.order_id,
            "status": self.status,
            "return_type": self.return_type,
            "refund_amount": str(self.refund_amount),
            "refund_method": self.refund_method,
            "reason_note": self.reason_note,
        }


class ReturnItem(db.Model):
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    return_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    restock: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_item_id": self.order_item_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "condition": self.condition,
            "restock": self.restock,
            "refund_amount": str(self.refund_amount),
        }
