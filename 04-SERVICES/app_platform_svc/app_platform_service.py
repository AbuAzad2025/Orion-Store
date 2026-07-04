from __future__ import annotations

import uuid

from app_platform.app_platform import (
    AppInstallation,
    AppWebhookSubscription,
    OAuthApplication,
    SandboxStore,
)
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class AppPlatformService:
    def register_app(
        self,
        *,
        tenant_id: int,
        name: str,
        redirect_uris: list,
        scopes: list | None = None,
    ) -> OAuthApplication:
        client_id = uuid.uuid4().hex
        app = OAuthApplication(
            tenant_id=tenant_id,
            name=name,
            redirect_uris=redirect_uris,
            client_id=client_id,
            client_secret_hash=uuid.uuid4().hex,
            scopes=scopes or [],
        )
        db.session.add(app)
        db.session.commit()
        return app

    def install_app(
        self, *, tenant_id: int, app_id: int, installed_by: int
    ) -> AppInstallation:
        app = OAuthApplication.query.filter_by(id=app_id).first()
        if not app or not app.is_active:
            raise NotFoundError("Application not found or inactive.")
        existing = AppInstallation.query.filter_by(
            tenant_id=tenant_id, app_id=app_id, is_active=True
        ).first()
        if existing:
            return existing
        inst = AppInstallation(
            tenant_id=tenant_id,
            app_id=app_id,
            installed_by=installed_by,
            access_token_hash=uuid.uuid4().hex,
        )
        db.session.add(inst)
        db.session.commit()
        return inst

    def subscribe_webhook(
        self, *, tenant_id: int, installation_id: int, topic: str, callback_url: str
    ) -> AppWebhookSubscription:
        sub = AppWebhookSubscription(
            tenant_id=tenant_id,
            installation_id=installation_id,
            topic=topic,
            callback_url=callback_url,
        )
        db.session.add(sub)
        db.session.commit()
        return sub

    def create_sandbox(
        self, *, tenant_id: int, slug: str, name: str, expires_at: str
    ) -> SandboxStore:
        sb = SandboxStore(
            tenant_id=tenant_id, slug=slug, name=name, expires_at=expires_at
        )
        db.session.add(sb)
        db.session.commit()
        return sb
