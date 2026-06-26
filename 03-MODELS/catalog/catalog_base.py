"""Shared mixins for tenant-scoped catalog tables."""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import SoftDeleteMixin, TimestampMixin
from base.pk import PrimaryKeyType


class TenantCatalogMixin(TimestampMixin, SoftDeleteMixin):
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
