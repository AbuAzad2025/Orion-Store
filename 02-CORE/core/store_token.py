"""Signed, expiring storefront tenant tokens.

A plain ``?tenant_slug=...`` value is guessable and can be swapped to browse
another tenant. These tokens are signed and timestamped with the application
secret: tampering or expiry invalidates them and the request gets no tenant.
"""

from __future__ import annotations

import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT = "orion-store-token"
MAX_AGE = 7 * 24 * 3600  # one week; tokens only grant public storefront access


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT)


def issue(tenant) -> str:
    """Return a signed, timestamped token identifying this tenant."""
    return _serializer().dumps({"tid": str(tenant.public_id)})


def resolve(token: str | None, max_age: int = MAX_AGE):
    """Resolve a token to an active tenant, or ``None`` if invalid/expired."""
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not data.get("tid"):
        return None
    try:
        public_id = uuid.UUID(str(data["tid"]))
    except (ValueError, AttributeError, TypeError):
        return None
    from tenant.tenant import Tenant

    return Tenant.query.filter_by(
        public_id=public_id, is_active=True, deleted_at=None
    ).first()


def signed_url(url: str | None, token: str) -> str:
    """Return an image URL with exactly one fresh signed store token."""
    if not url:
        return ""
    parts = urlsplit(str(url))
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "store"]
    # Never leak the signed token to an external origin: only local product
    # images are served through the token-gated route.
    local = (
        not parts.scheme
        and not parts.netloc
        and parts.path.startswith("/store/static/images/products/")
    )
    if token and local:
        query.append(("store", token))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
