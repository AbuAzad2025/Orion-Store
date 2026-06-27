"""Shipping zone model (§4.7, wave 6 #58)."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from catalog.catalog_base import TenantCatalogMixin
from orion.extensions import db


class ShippingZone(db.Model, TenantCatalogMixin):
    __tablename__ = "shipping_zones"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    countries: Mapped[list | None] = mapped_column(db.JSON, nullable=True)
    regions: Mapped[list | None] = mapped_column(db.JSON, nullable=True)
    postal_codes: Mapped[list | None] = mapped_column(db.JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "countries": self.countries or [],
            "regions": self.regions or [],
            "is_default": self.is_default,
            "is_active": self.is_active,
        }
