from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class GiftRegistry(db.Model, TimestampMixin):
    __tablename__ = "gift_registries"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=True)
    event_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "user_id": self.user_id,
            "registry_name": self.registry_name,
            "event_type": self.event_type,
            "event_date": self.event_date,
            "is_public": self.is_public,
            "slug": self.slug,
        }


class GiftRegistryItem(db.Model):
    __tablename__ = "gift_registry_items"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    registry_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("gift_registries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    requested_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    purchased_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "requested_quantity": self.requested_quantity,
            "purchased_quantity": self.purchased_quantity,
        }
