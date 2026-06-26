"""Product model (§4.4, wave 2 #22)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import SoftDeleteMixin, TimestampMixin, VersionMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class Product(db.Model, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", "tenant_id", name="uq_products_slug"),
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        CheckConstraint("quantity >= 0", name="ck_products_qty_nonneg"),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    compare_at_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    category_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    brand_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "public_id": str(self.public_id),
            "name": self.name,
            "slug": self.slug,
            "sku": self.sku,
            "price": str(self.price),
            "quantity": self.quantity,
            "is_published": self.is_published,
            "category_id": self.category_id,
            "brand_id": self.brand_id,
        }
