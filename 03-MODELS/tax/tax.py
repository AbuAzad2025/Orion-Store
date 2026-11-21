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


class TaxJurisdiction(db.Model, TimestampMixin):
    __tablename__ = "tax_jurisdictions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tax_jurisdictions"),
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
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "country_code": self.country_code,
            "country": self.country_code,
            "region": self.region,
            "is_active": self.is_active,
            "rates": [
                r.to_dict()
                for r in TaxRate.query.filter_by(
                    tenant_id=self.tenant_id, jurisdiction_id=self.id
                ).all()
            ],
        }


class TaxRate(db.Model, TimestampMixin):
    __tablename__ = "tax_rates"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "product_tax_code", name="uq_tax_rates"),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    jurisdiction_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tax_jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    product_tax_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "rate": str(self.rate),
            "product_tax_code": self.product_tax_code,
            "is_compound": self.is_compound,
            "priority": self.priority,
        }


class TaxNexusRule(db.Model, TimestampMixin):
    __tablename__ = "tax_nexus_rules"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tax_jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
    )
    nexus_type: Mapped[str] = mapped_column(
        String(20), default="physical", nullable=False
    )
    threshold_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    threshold_transactions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "nexus_type": self.nexus_type,
            "threshold_amount": (
                str(self.threshold_amount) if self.threshold_amount else None
            ),
            "threshold_transactions": self.threshold_transactions,
        }
