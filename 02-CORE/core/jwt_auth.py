"""JWT token helpers (§0.5, §3.5)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Response, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
)

from orion.extensions import db
from user.user import User


def issue_tokens_for_user(user: User) -> dict[str, str]:
    identity = str(user.public_id)
    claims: dict[str, Any] = {
        "is_superuser": user.is_superuser,
        "tenant_id": user.tenant_id,
    }
    return {
        "access_token": create_access_token(
            identity=identity, additional_claims=claims
        ),
        "refresh_token": create_refresh_token(
            identity=identity, additional_claims=claims
        ),
    }


def set_jwt_cookies(response: Response, tokens: dict[str, str]) -> Response:
    set_access_cookies(response, tokens["access_token"])
    set_refresh_cookies(response, tokens["refresh_token"])
    return response


def _canonical_identity(identity: str | None) -> str | None:
    """Persist only a canonical UUID; fail closed to NULL for anything else.

    Compensating control for ADR 0003 (NEVER-APPLY of the FK from
    revoked_tokens.user_public_id to users.public_id).
    """
    if not identity:
        return None
    try:
        return str(uuid.UUID(str(identity)))
    except (ValueError, TypeError, AttributeError):
        return None


def _revoke(jti: str, token_type: str, expires_at, identity: str | None) -> None:
    from platform_models.revoked_token import RevokedToken

    if not jti or RevokedToken.is_revoked(jti):
        return
    if not isinstance(expires_at, datetime):
        expires_at = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    db.session.add(
        RevokedToken(
            jti=jti,
            token_type=token_type,
            user_public_id=_canonical_identity(identity),
            expires_at=expires_at,
        )
    )


def revoke_current_tokens() -> None:
    """Blocklist the current access token and the refresh cookie (if any)."""
    identity = None
    try:
        claims = get_jwt()
        identity = get_jwt_identity()
        _revoke(
            claims.get("jti", ""),
            claims.get("type", "access"),
            claims.get("exp"),
            str(identity) if identity else None,
        )
    except RuntimeError:
        pass  # e.g. HTML logout without a valid JWT cookie
    refresh = request.cookies.get(
        current_app.config.get("JWT_REFRESH_COOKIE_NAME", "refresh_token_cookie")
    )
    if refresh:
        try:
            claims = decode_token(refresh)
            _revoke(
                claims.get("jti", ""),
                "refresh",
                claims.get("exp"),
                str(claims.get("sub") or identity or "") or None,
            )
        except Exception:
            pass
    db.session.commit()


def install_token_blocklist(jwt_manager) -> None:
    """Make every JWT check the revocation ledger before accepting a token."""

    @jwt_manager.token_in_blocklist_loader
    def _is_revoked(_header, payload):
        from platform_models.revoked_token import RevokedToken

        return RevokedToken.is_revoked(payload.get("jti"))
