from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class WorkflowDefinition(db.Model, TimestampMixin):
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    conditions: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)
    actions: Mapped[list] = mapped_column(db.JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "conditions": self.conditions,
            "actions": self.actions,
            "is_active": self.is_active,
        }


class WorkflowRun(db.Model, TimestampMixin):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    definition_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "status": self.status,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
