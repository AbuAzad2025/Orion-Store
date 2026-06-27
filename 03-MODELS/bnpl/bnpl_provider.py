"""BNPL provider config per tenant (§4.23, wave 8 #62)."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class BnplProvider(db.Model, TimestampMixin):
    __tablename__ = "bnpl_providers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_bnpl_providers_tenant"),
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
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    merchant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(db.JSON, default=dict)

    def to_dict(self) -> dict:
        from core.crypto import strip_gateway_secrets

        return strip_gateway_secrets(
            {
                "id": self.id,
                "provider": self.provider,
                "is_enabled": self.is_enabled,
                "merchant_id": self.merchant_id,
                "api_credentials_encrypted": self.api_credentials_encrypted,
                "config": self.config or {},
            }
        )
