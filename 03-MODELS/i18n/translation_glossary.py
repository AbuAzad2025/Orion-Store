"""Translation glossary model (§4.15)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class TranslationGlossary(db.Model):
    __tablename__ = "translation_glossary"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int | None] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_locale: Mapped[str] = mapped_column(String(5), nullable=False)
    target_locale: Mapped[str] = mapped_column(String(5), nullable=False)
    source_term: Mapped[str] = mapped_column(String(255), nullable=False)
    target_term: Mapped[str] = mapped_column(String(255), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "source_locale": self.source_locale,
            "target_locale": self.target_locale,
            "source_term": self.source_term,
            "target_term": self.target_term,
        }
