"""Per-tenant store configuration (§4.2)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base.pk import PrimaryKeyType

from orion.extensions import db


class TenantConfig(db.Model):
    __tablename__ = "tenant_configs"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True
    )
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    tax_included: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_guest_checkout: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="config")
