"""Brand model (§4.4, wave 2 #22)."""

from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from catalog.catalog_base import TenantCatalogMixin
from orion.extensions import db


class Brand(db.Model, TenantCatalogMixin):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("slug", "tenant_id", name="uq_brands_slug"),)

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "slug": self.slug}
