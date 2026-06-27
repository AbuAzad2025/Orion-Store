"""Shipping rate — method × zone pricing (§4.7, wave 6 #58)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class ShippingRate(db.Model, TimestampMixin):
    __tablename__ = "shipping_rates"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shipping_method_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("shipping_methods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shipping_zone_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("shipping_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "shipping_method_id": self.shipping_method_id,
            "shipping_zone_id": self.shipping_zone_id,
            "price": str(self.price),
        }
