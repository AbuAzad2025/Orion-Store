"""Impersonation session model (AZ-0.18)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class ImpersonationSession(db.Model):
    __tablename__ = "impersonation_sessions"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    impersonator_user_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "impersonator_user_id": self.impersonator_user_id,
            "target_user_id": self.target_user_id,
            "tenant_id": self.tenant_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "revoked": self.revoked,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
        }

    def is_active(self) -> bool:
        from core.utils import utc_now

        return (
            not self.revoked and self.ended_at is None and self.expires_at > utc_now()
        )
