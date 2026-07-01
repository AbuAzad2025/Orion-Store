from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class AffiliateProgram(db.Model, TimestampMixin):
    __tablename__ = "affiliate_programs"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_aff_programs"),)

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    commission_type: Mapped[str] = mapped_column(String(20), default="percentage", nullable=False)
    commission_value: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cookie_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "commission_type": self.commission_type,
            "commission_value": str(self.commission_value),
            "cookie_days": self.cookie_days,
            "is_active": self.is_active,
        }


class Affiliate(db.Model, TimestampMixin):
    __tablename__ = "affiliates"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("affiliate_programs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    referral_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    total_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "email": self.email,
            "referral_code": self.referral_code,
            "is_active": self.is_active,
            "total_earned": str(self.total_earned),
            "total_paid": str(self.total_paid),
        }


class AffiliateCommission(db.Model, TimestampMixin):
    __tablename__ = "affiliate_commissions"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "affiliate_id": self.affiliate_id,
            "order_id": self.order_id,
            "amount": str(self.amount),
            "status": self.status,
        }


class AffiliateLink(db.Model, TimestampMixin):
    __tablename__ = "affiliate_links"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    affiliate_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(PrimaryKeyType, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "product_id": self.product_id, "url": self.url, "click_count": self.click_count}
