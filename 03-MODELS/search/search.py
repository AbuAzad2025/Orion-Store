from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class SearchSynonym(db.Model, TimestampMixin):
    __tablename__ = "search_synonyms"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    synonyms: Mapped[list] = mapped_column(db.JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "term": self.term,
            "synonyms": self.synonyms,
            "is_active": self.is_active,
        }


class SearchRedirect(db.Model, TimestampMixin):
    __tablename__ = "search_redirects"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_term: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query_term": self.query_term,
            "redirect_url": self.redirect_url,
            "is_active": self.is_active,
        }


class SearchBoostRule(db.Model, TimestampMixin):
    __tablename__ = "search_boost_rules"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )
    boost_factor: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    query_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "category_id": self.category_id,
            "boost_factor": self.boost_factor,
            "query_keyword": self.query_keyword,
        }
