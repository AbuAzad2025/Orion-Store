"""Signed, tamper-evident storefront tenant tokens.

A plain ``?tenant_slug=...`` value is guessable and can be swapped to browse
another tenant. These tokens are signed with the application secret: changing
even one character invalidates the signature and the request gets no tenant.
"""

from __future__ import annotations

import uuid

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

SALT = "orion-store-token"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt=SALT)


def issue(tenant) -> str:
    """Return a signed token identifying this tenant."""
    return _serializer().dumps({"tid": str(tenant.public_id)})


def resolve(token: str | None):
    """Resolve a signed token to an active tenant, or ``None`` if tampered."""
    if not token:
        return None
    try:
        data = _serializer().loads(token)
    except (BadSignature, ValueError, TypeError):
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
