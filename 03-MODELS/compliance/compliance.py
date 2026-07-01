from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class ConsentRecord(db.Model, TimestampMixin):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "consent_type": self.consent_type,
            "granted": self.granted,
            "ip_address": self.ip_address,
        }


class DataSubjectRequest(db.Model, TimestampMixin):
    __tablename__ = "data_subject_requests"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "request_type": self.request_type,
            "status": self.status,
        }


class CookieConsentSetting(db.Model, TimestampMixin):
    __tablename__ = "cookie_consent_settings"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    necessary_cookies: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)
    analytics_cookies: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)
    marketing_cookies: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)
    banner_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "is_active": self.is_active,
            "banner_message": self.banner_message,
        }


class SsoProvider(db.Model, TimestampMixin):
    __tablename__ = "sso_providers"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(PrimaryKeyType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_type": self.provider_type,
            "issuer_url": self.issuer_url,
            "is_active": self.is_active,
            "auto_provision": self.auto_provision,
        }
