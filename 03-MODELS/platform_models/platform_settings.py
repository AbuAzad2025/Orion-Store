"""Platform singleton settings (§4.48, wave 2 #19)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from orion.extensions import db


class PlatformSettings(db.Model):
    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform_name: Mapped[str] = mapped_column(String(100), default="Azadexa")
    platform_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform_logo_dark_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    footer_html: Mapped[str] = mapped_column(Text, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(200), default="Ahmad Ghannam")
    owner_phone: Mapped[str] = mapped_column(String(50), default="0562150193")
    owner_phone_intl: Mapped[str] = mapped_column(String(50), default="+972562150193")
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.0100")
    )
    singleton: Mapped[str] = mapped_column(String(1), default="1", nullable=False)
    valuepayment_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    valuepayment_config: Mapped[dict] = mapped_column(db.JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            "platform_name": self.platform_name,
            "platform_logo_url": self.platform_logo_url,
            "owner_name": self.owner_name,
            "owner_phone": self.owner_phone,
            "owner_phone_intl": self.owner_phone_intl,
            "owner_email": self.owner_email,
            "default_commission_percent": str(self.default_commission_percent),
            "valuepayment_enabled": self.valuepayment_enabled,
        }
