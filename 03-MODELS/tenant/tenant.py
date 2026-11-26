"""Tenant model — multi-tenant root entity (§4.2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base.pk import PrimaryKeyType
from base.types import PlanType, TenantStatus
from orion.extensions import db

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from tenant.tenant_config import TenantConfig


class Tenant(db.Model):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="PS", nullable=False)
    default_language: Mapped[str] = mapped_column(
        String(5), default="ar", nullable=False
    )
    default_currency: Mapped[str] = mapped_column(
        String(3), default="ILS", nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Jerusalem", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=TenantStatus.PENDING.value, nullable=False
    )
    plan_type: Mapped[str] = mapped_column(
        String(20), default=PlanType.FREE.value, nullable=False
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform_commission_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    config: Mapped["TenantConfig"] = relationship(
        "TenantConfig", back_populates="tenant", uselist=False, lazy="joined"
    )

    def name_for(self, locale: str | None = None) -> str:
        code = (locale or "").split("_")[0].lower()
        return self.name_en if code == "en" and self.name_en else self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "public_id": str(self.public_id),
            "is_active": self.is_active,
            "custom_domain": self.custom_domain,
            "name": self.name,
            "name_en": self.name_en,
            "logo_url": self.logo_url,
            "slug": self.slug,
            "domain": self.domain,
            "status": self.status,
            "email": self.email,
        }
