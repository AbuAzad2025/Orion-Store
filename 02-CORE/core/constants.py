"""Shared constants — Azadexa v1.10."""

from __future__ import annotations

from decimal import Decimal

# Commission resolution order (§0.13.2)
COMMISSION_FALLBACK_CHAIN: list[str | Decimal] = [
    "tenants.platform_commission_percent",
    "platform_settings.default_commission_percent",
    Decimal("0.0100"),
]

# Search: sync trigger below this count; above → Celery bulk reindex
SEARCH_VECTOR_SYNC_LIMIT = 1000

# API: never expose these fields in GET JSON responses (§0.14)
GATEWAY_RESPONSE_DENYLIST: tuple[str, ...] = (
    "webhook_secret",
    "credentials_encrypted",
)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
