"""OMS warehouse and inventory (§4.21, wave 9 #63)."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class Warehouse(db.Model, TimestampMixin):
    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_warehouses_code"),)

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_pickup_location: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "is_active": self.is_active,
            "is_pickup_location": self.is_pickup_location,
            "priority": self.priority,
        }


class InventoryLevel(db.Model, TimestampMixin):
    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id", "product_id", name="uq_inventory_levels_wh_product"
        ),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    warehouse_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "reserved_quantity": self.reserved_quantity,
            "available": self.quantity - self.reserved_quantity,
        }
