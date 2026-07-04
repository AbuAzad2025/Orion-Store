from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class AccessibilityAudit(db.Model, TimestampMixin):
    __tablename__ = "accessibility_audits"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    issues: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "page_url": self.page_url,
            "score": self.score,
            "issues": self.issues,
        }
