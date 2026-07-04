"""HTTP header builders for Flask test_client."""

from __future__ import annotations


def auth_headers(
    user, *, app, tenant_id: str | None = None, claims=None
) -> dict[str, str]:
    from flask_jwt_extended import create_access_token

    headers = {
        "Authorization": f"Bearer {create_access_token(identity=str(user.public_id))}"
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
    return auth_headers(user, app=None, tenant_id=tenant_slug)
