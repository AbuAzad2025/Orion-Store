"""B2B customer group (§4.18, wave 9 #63)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class CustomerGroup(db.Model, TimestampMixin):
    __tablename__ = "customer_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_customer_groups_code"),
    )

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    price_list_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("price_lists.id", ondelete="SET NULL"), nullable=True
    )
    min_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_wholesale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "discount_percent": str(self.discount_percent),
            "price_list_id": self.price_list_id,
            "payment_terms_days": self.payment_terms_days,
            "is_wholesale": self.is_wholesale,
        }


class CustomerGroupMember(db.Model):
    __tablename__ = "customer_group_members"

    customer_group_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("customer_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
