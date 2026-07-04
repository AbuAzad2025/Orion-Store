from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class InventoryTransfer(db.Model, TimestampMixin):
    __tablename__ = "inventory_transfers"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transfer_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    from_warehouse_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    to_warehouse_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "transfer_number": self.transfer_number,
            "from_warehouse_id": self.from_warehouse_id,
            "to_warehouse_id": self.to_warehouse_id,
            "status": self.status,
            "notes": self.notes,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class InventoryTransferItem(db.Model):
    __tablename__ = "inventory_transfer_items"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    transfer_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("inventory_transfers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
        }
