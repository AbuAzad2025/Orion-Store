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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class DraftOrder(db.Model, TimestampMixin):
    __tablename__ = "draft_orders"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    shipping_address: Mapped[dict] = mapped_column(db.JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    send_email_invite: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    converted_order_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "draft_number": self.draft_number,
            "customer_email": self.customer_email,
            "notes": self.notes,
            "status": self.status,
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "shipping_cost": str(self.shipping_cost),
            "discount_amount": str(self.discount_amount),
            "total": str(self.total),
            "converted_order_id": self.converted_order_id,
        }


class DraftOrderItem(db.Model):
    __tablename__ = "draft_order_items"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    draft_order_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("draft_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_name": self.product_name,
            "product_sku": self.product_sku,
            "unit_price": str(self.unit_price),
            "quantity": self.quantity,
            "total_price": str(self.total_price),
        }
