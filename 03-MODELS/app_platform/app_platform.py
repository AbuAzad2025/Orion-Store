from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from base.base_model import TimestampMixin
from base.pk import PrimaryKeyType
from orion.extensions import db


class OAuthApplication(db.Model, TimestampMixin):
    __tablename__ = "oauth_applications"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_uris: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scopes: Mapped[list] = mapped_column(db.JSON, default=list, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "client_id": self.client_id,
            "is_active": self.is_active,
            "scopes": self.scopes,
        }


class AppInstallation(db.Model, TimestampMixin):
    __tablename__ = "app_installations"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("oauth_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    installed_by: Mapped[int] = mapped_column(
        PrimaryKeyType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    access_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "is_active": self.is_active,
        }


class AppWebhookSubscription(db.Model, TimestampMixin):
    __tablename__ = "app_webhook_subscriptions"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installation_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("app_installations.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    callback_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Shared HMAC signing secret returned to the subscriber once. Consistent
    # with tenant_payment_gateways.webhook_secret (raw, not a password hash):
    # the verifier needs the key itself to recompute the signature.
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "callback_url": self.callback_url,
            "webhook_secret": self.webhook_secret,
            "is_active": self.is_active,
        }


class SandboxStore(db.Model, TimestampMixin):
    __tablename__ = "sandbox_stores"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
        }
