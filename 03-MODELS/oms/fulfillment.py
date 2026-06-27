"""OMS fulfillment models (§4.21, wave 9 #63)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class Fulfillment(db.Model, TimestampMixin):
    __tablename__ = "fulfillments"

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
    warehouse_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fulfillment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fulfillment_number": self.fulfillment_number,
            "order_id": self.order_id,
            "warehouse_id": self.warehouse_id,
            "status": self.status,
            "tracking_number": self.tracking_number,
        }


class FulfillmentItem(db.Model):
    __tablename__ = "fulfillment_items"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    fulfillment_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("fulfillments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_item_id": self.order_item_id,
            "quantity": self.quantity,
        }
