"""HTTP header builders for Flask test_client."""

from __future__ import annotations


def auth_headers(
    user, *, app=None, tenant_id: str | None = None, claims=None
) -> dict[str, str]:
    from flask_jwt_extended import create_access_token

    if isinstance(user, str):
        identity = user
    elif hasattr(user, "public_id"):
        identity = user.public_id
    else:
        identity = None
    if identity is None:
        raise TypeError("auth_headers expects a user object or public_id string.")
    headers = {
        "Authorization": f"Bearer {create_access_token(identity=str(identity))}"
    }
    headers["Content-Type"] = "application/json"
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    if claims:
        headers.update(claims)
    return headers


def bearer_headers(token: str, *, tenant_id: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def tenant_headers(user, *, tenant_slug: str | None = None) -> dict[str, str]:
    if tenant_slug is None:
        slug = getattr(user, "slug", None)
        if slug is None and isinstance(user, str):
            slug = user
        if slug is None:
            raise TypeError("tenant_headers expects a tenant object or `tenant_slug` keyword.")
        tenant_slug = slug
    return auth_headers(user, app=None, tenant_id=tenant_slug)
