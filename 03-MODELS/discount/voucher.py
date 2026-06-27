"""Voucher model (§4.8, wave 6 #59)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from catalog.catalog_base import TenantCatalogMixin
from orion.extensions import db


class Voucher(db.Model, TenantCatalogMixin):
    __tablename__ = "vouchers"
    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_vouchers_code_tenant"),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), default="percentage")
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_free_shipping: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "value": str(self.value),
            "min_order_value": (
                str(self.min_order_value) if self.min_order_value is not None else None
            ),
            "max_discount_amount": (
                str(self.max_discount_amount)
                if self.max_discount_amount is not None
                else None
            ),
            "usage_limit": self.usage_limit,
            "usage_count": self.usage_count,
            "is_free_shipping": self.is_free_shipping,
            "is_active": self.is_active,
        }
