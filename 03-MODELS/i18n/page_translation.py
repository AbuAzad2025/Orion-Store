"""Page translation model (§4.15)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class PageTranslation(db.Model):
    __tablename__ = "page_translations"
    __table_args__ = (
        UniqueConstraint("page_id", "locale", name="uq_page_trans_locale"),
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
    page_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("cms_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_dict(self) -> dict:
        return {
            "locale": self.locale,
            "title": self.title,
            "body": self.body,
            "slug": self.slug,
        }
