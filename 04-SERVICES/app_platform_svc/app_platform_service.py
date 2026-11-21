from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid

from app_platform.app_platform import (
    AppInstallation,
    AppWebhookSubscription,
    OAuthApplication,
    SandboxStore,
)

from core.exceptions import AuthenticationError, NotFoundError, ValidationError
from core.jwt_auth import create_access_token
from orion.extensions import db


def hash_client_secret(raw_secret: str) -> str:
    """Salted SHA-256 of a raw OAuth client secret, stored as ``salt$digest``.

    The raw secret is never persisted. A fresh random salt makes identical
    secrets produce different stored values and defeats precomputed hashes.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{raw_secret}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_client_secret(raw_secret: str, stored: str) -> bool:
    """Constant-time verification of a raw secret against its salted digest."""
    try:
        salt, digest = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False
    computed = hashlib.sha256(f"{salt}{raw_secret}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, digest)


def _normalize_scopes(scopes: list | str | None) -> list[str]:
    """Accept both a JSON list and a space-separated string from API clients."""
    if scopes is None:
        return []
    if isinstance(scopes, str):
        return scopes.split()
    return [str(s) for s in scopes]


def _lookup_app_by_client_id(client_id: str) -> OAuthApplication | None:
    """Find an app by its globally unique client_id.

    The oauth_applications table is tenant RLS-protected, while the OAuth token
    endpoint has no user/tenant context. Elevate only for this narrow lookup
    (the secret is still verified before any token is issued) and restore the
    previous RLS flag immediately afterwards.
    """
    previous = None
    elevated = False
    if db.engine.dialect.name == "postgresql":
        previous = db.session.execute(
            db.text("SELECT current_setting('app.is_platform_admin', true)")
        ).scalar()
        db.session.execute(
            db.text("SELECT set_config('app.is_platform_admin', 'true', true)")
        )
        elevated = True
    try:
        return OAuthApplication.query.filter_by(client_id=client_id).first()
    finally:
        if elevated:
            db.session.execute(
                db.text("SELECT set_config('app.is_platform_admin', :v, true)"),
                {"v": previous or "false"},
            )


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
        raw_secret = secrets.token_urlsafe(32)
        app = OAuthApplication(
            tenant_id=tenant_id,
            name=name,
            redirect_uris=redirect_uris,
            client_id=client_id,
            client_secret_hash=hash_client_secret(raw_secret),
            scopes=_normalize_scopes(scopes),
        )
        db.session.add(app)
        db.session.commit()
        # Transient (non-persisted) attribute: lets the HTTP layer return the
        # raw secret exactly once at registration. Never read it from storage.
        app._raw_client_secret = raw_secret
        return app

    def issue_oauth_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        grant_type: str = "client_credentials",
    ) -> dict:
        """Validate client_credentials and issue a short-lived signed JWT.

        The token carries ``scope`` and ``app_id`` as additional claims so a
        resource server can authorise the external app without a user session.
        """
        if grant_type != "client_credentials":
            raise ValidationError("Unsupported grant_type.")

        app = _lookup_app_by_client_id(client_id)
        if not app or not app.is_active:
            raise AuthenticationError("Invalid client credentials.")
        if not verify_client_secret(client_secret or "", app.client_secret_hash):
            raise AuthenticationError("Invalid client credentials.")

        allowed = _normalize_scopes(app.scopes)
        requested = _normalize_scopes(scope)
        if requested:
            unsupported = [s for s in requested if s not in allowed]
            if unsupported:
                raise ValidationError("Unsupported scope(s): " + ", ".join(unsupported))
            granted = requested
        else:
            granted = allowed

        claims = {
            "scope": " ".join(granted),
            "app_id": app.id,
            "tenant_id": app.tenant_id,
        }
        token = create_access_token(identity=app.client_id, additional_claims=claims)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "scope": claims["scope"],
            "app_id": app.id,
        }

    def install_app(
        self, *, tenant_id: int, app_id: int, installed_by: int
    ) -> AppInstallation:
        app = OAuthApplication.query.filter_by(id=app_id, tenant_id=tenant_id).first()
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
        installation = AppInstallation.query.filter_by(
            id=installation_id, tenant_id=tenant_id, is_active=True
        ).first()
        if not installation:
            raise NotFoundError("Installation not found.")
        sub = AppWebhookSubscription(
            tenant_id=tenant_id,
            installation_id=installation_id,
            topic=topic,
            callback_url=callback_url,
            webhook_secret=secrets.token_urlsafe(32),
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
