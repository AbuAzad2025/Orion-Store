from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class PodConnection(db.Model, TimestampMixin):
    __tablename__ = "pod_connections"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "provider": self.provider, "api_url": self.api_url, "is_active": self.is_active}


class DropshipSupplier(db.Model, TimestampMixin):
    __tablename__ = "dropship_suppliers"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fulfillment_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "fulfillment_time_days": self.fulfillment_time_days,
            "is_active": self.is_active,
        }


class DropshipOrder(db.Model, TimestampMixin):
    __tablename__ = "dropship_orders"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("dropship_suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    supplier_order_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "supplier_id": self.supplier_id,
            "order_id": self.order_id,
            "supplier_order_ref": self.supplier_order_ref,
            "status": self.status,
            "cost": str(self.cost),
        }
