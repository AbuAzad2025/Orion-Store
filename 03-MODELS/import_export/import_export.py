from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class ImportExportJob(db.Model, TimestampMixin):
    __tablename__ = "import_export_jobs"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "entity_type": self.entity_type,
            "status": self.status,
            "file_url": self.file_url,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
        }
