from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class StockNotification(db.Model, TimestampMixin):
    __tablename__ = "stock_notifications"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "customer_email": self.customer_email,
            "is_notified": self.is_notified,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }
