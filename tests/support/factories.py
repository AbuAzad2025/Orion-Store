"""Test data builders — keep payloads DRY across API/integration tests."""

from __future__ import annotations

from typing import Any


def tenant_create_payload(
    *,
    name: str = "Demo Store",
    slug: str = "demo-store",
    email: str = "demo@store.com",
    admin_email: str | None = "admin@demo.com",
    admin_password: str | None = "password123",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "slug": slug, "email": email}
    if admin_email and admin_password:
        payload["admin_email"] = admin_email
        payload["admin_password"] = admin_password
    return payload
