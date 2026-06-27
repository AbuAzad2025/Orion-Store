"""Tenant payment gateway (§4.49, wave 4 #40)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class TenantPaymentGateway(db.Model):
    __tablename__ = "tenant_payment_gateways"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    config: Mapped[dict] = mapped_column(db.JSON, default=dict)
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        from core.crypto import strip_gateway_secrets

        return strip_gateway_secrets(
            {
                "id": self.id,
                "provider": self.provider,
                "display_name": self.display_name,
                "is_enabled": self.is_enabled,
                "status": self.status,
                "webhook_secret": self.webhook_secret,
                "credentials_encrypted": self.credentials_encrypted,
            }
        )
