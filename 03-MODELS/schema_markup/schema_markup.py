from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class ProductSchemaMarkup(db.Model, TimestampMixin):
    __tablename__ = "product_schema_markup"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    schema_type: Mapped[str] = mapped_column(String(50), default="Product", nullable=False)
    json_ld: Mapped[dict] = mapped_column(db.JSON, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "product_id": self.product_id, "schema_type": self.schema_type, "json_ld": self.json_ld}
