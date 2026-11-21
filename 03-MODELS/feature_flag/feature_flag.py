"""Feature flag definition (§4.13, wave 7 #61)."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class FeatureFlag(db.Model, TimestampMixin):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    default_value: Mapped[bool] = mapped_column(Boolean, default=False)
    scope: Mapped[str] = mapped_column(String(20), default="tenant")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    rollout_percent: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "default_value": self.default_value,
            "scope": self.scope,
            "rollout_percent": self.rollout_percent,
        }


class TenantFeatureFlagOverride(db.Model, TimestampMixin):
    __tablename__ = "tenant_feature_flag_overrides"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "flag_id", name="uq_tenant_feature_flag_override_tenant"
        ),
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
    flag_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("feature_flags.id", ondelete="CASCADE"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    set_by: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "flag_id": self.flag_id,
            "tenant_id": self.tenant_id,
            "enabled": self.enabled,
            "reason": self.reason,
            "set_by": self.set_by,
        }
