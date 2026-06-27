"""CMS page model (§4.15, wave 15)."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class CmsPage(db.Model, TimestampMixin):
    __tablename__ = "cms_pages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_cms_pages_tenant_slug"),
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
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "is_published": self.is_published,
        }
