from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class CurrencyRate(db.Model, TimestampMixin):
    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint(
            "from_currency", "to_currency", "rate_date", name="uq_currency_rates"
        ),
    )

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    rate_date: Mapped[str] = mapped_column(
        Date, server_default=func.current_date(), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), default="manual")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": str(self.rate),
            "rate_date": str(self.rate_date),
            "source": self.source,
        }
