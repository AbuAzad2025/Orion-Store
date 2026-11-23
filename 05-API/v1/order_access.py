"""Helpers for safely exposing storefront orders to browsers."""

from __future__ import annotations

from flask import current_app, g

_SENSITIVE_KEYS = (
    "customer_email",
    "user_id",
    "shipping_address",
    "billing_address",
    "phone",
)


def is_order_owner(order) -> bool:
    """True when the authenticated user owns the order (or administers it)."""
    user = getattr(g, "user", None)
    if user is None:
        return False
    if getattr(g, "is_platform_admin", False):
        return True
    if getattr(user, "is_admin", False) and user.tenant_id == order.tenant_id:
        return True
    if order.user_id is not None and order.user_id == user.id:
        return True
    return (order.customer_email or "").lower() == (
        getattr(user, "email", None) or ""
    ).lower()


def public_order_payload(order) -> dict:
    """Never leak PII to an anonymous holder of an opaque order URL."""
    data = order.to_dict()
    if not is_order_owner(order):
        for key in _SENSITIVE_KEYS:
            data.pop(key, None)
    return data


def _serializer():
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="orion-order-access"
    )


def order_access_token(order) -> str:
    """Signed capability for guest order lookups (7 days)."""
    return _serializer().dumps({"oid": str(order.public_id)})


def verify_order_access_token(token, order, max_age: int = 7 * 24 * 3600) -> bool:
    """Verify a signed guest capability for this specific order."""
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=max_age)
    except Exception:
        return False
    return isinstance(data, dict) and str(data.get("oid")) == str(order.public_id)
