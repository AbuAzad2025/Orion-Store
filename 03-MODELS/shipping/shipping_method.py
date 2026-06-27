"""Shipping method model (§4.7, wave 6 #58)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from catalog.catalog_base import TenantCatalogMixin
from orion.extensions import db


class ShippingMethod(db.Model, TenantCatalogMixin):
    __tablename__ = "shipping_methods"
    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_shipping_methods_code_tenant"),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    type: Mapped[str] = mapped_column(String(20), default="flat_rate")
    base_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    free_shipping_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    min_order_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    max_order_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    estimated_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "type": self.type,
            "base_cost": str(self.base_cost),
            "free_shipping_threshold": (
                str(self.free_shipping_threshold)
                if self.free_shipping_threshold is not None
                else None
            ),
            "is_default": self.is_default,
            "is_active": self.is_active,
            "estimated_days_min": self.estimated_days_min,
            "estimated_days_max": self.estimated_days_max,
        }
