"""SQLAlchemy base model and shared mixins (§4.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from orion.extensions import db


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class PublicIdMixin:
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )


class TenantScopedMixin:
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class BaseModel(db.Model, TimestampMixin, SoftDeleteMixin, PublicIdMixin, VersionMixin):
    """Abstract base for operational tables — wave 0 shell."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    def to_dict(self) -> dict:
        return {"id": self.id, "public_id": str(self.public_id)}
