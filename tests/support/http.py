"""HTTP header builders for Flask test_client."""

from __future__ import annotations


def auth_headers(user, *, app, tenant_id: str | None = None) -> dict[str, str]:
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity=str(user.public_id))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def bearer_headers(
    access_token: str, *, tenant_id: str | None = None
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def tenant_headers(slug_or_id: str) -> dict[str, str]:
    return {"X-Tenant-ID": slug_or_id}
