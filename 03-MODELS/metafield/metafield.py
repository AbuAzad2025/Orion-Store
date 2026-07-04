from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class MetafieldDefinition(db.Model, TimestampMixin):
    __tablename__ = "metafield_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_type", "key", name="uq_metafield_def"),
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
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(
        String(50), default="string", nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_rules: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_type": self.owner_type,
            "key": self.key,
            "label": self.label,
            "field_type": self.field_type,
            "is_required": self.is_required,
            "default_value": self.default_value,
        }


class Metafield(db.Model, TimestampMixin):
    __tablename__ = "metafields"
    __table_args__ = (
        UniqueConstraint("definition_id", "owner_id", name="uq_metafield_value"),
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
    definition_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("metafield_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(PrimaryKeyType, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    json_value: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "owner_id": self.owner_id,
            "value": self.value,
            "json_value": self.json_value,
        }
