from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class PlatformAuditReport(db.Model, TimestampMixin):
    __tablename__ = "platform_audit_reports"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    report_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    generated_by: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[dict] = mapped_column(db.JSON, default=dict, nullable=False)
    details: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_number": self.report_number,
            "report_type": self.report_type,
            "summary": self.summary,
            "generated_by": self.generated_by,
        }


class PlatformAdminAuditLog(db.Model):
    __tablename__ = "platform_admin_audit_log"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
        }
