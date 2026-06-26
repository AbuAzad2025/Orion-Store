"""External tenant subdomain registry — thin HTTP client (§3.10 boundary).

Tests patch ``integrations.external_registry.register_tenant_subdomain`` or
``requests.post`` — never the database layer.
"""

from __future__ import annotations

import os
from typing import Any

import requests

DEFAULT_TIMEOUT = 10


def register_tenant_subdomain(*, slug: str, tenant_id: int) -> dict[str, Any]:
    """Register tenant with external DNS / routing service."""
    registry_url = os.environ.get("TENANT_REGISTRY_URL", "").strip()
    if not registry_url:
        return {"status": "skipped", "reason": "TENANT_REGISTRY_URL not set"}

    response = requests.post(
        f"{registry_url.rstrip('/')}/tenants",
        json={"slug": slug, "tenant_id": tenant_id},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
