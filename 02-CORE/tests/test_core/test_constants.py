"""Tests for core.constants."""

from __future__ import annotations

from decimal import Decimal

from core.constants import (
    COMMISSION_FALLBACK_CHAIN,
    GATEWAY_RESPONSE_DENYLIST,
    SEARCH_VECTOR_SYNC_LIMIT,
)


def test_commission_fallback_chain_has_three_levels():
    assert len(COMMISSION_FALLBACK_CHAIN) == 3
    assert COMMISSION_FALLBACK_CHAIN[0] == "tenants.platform_commission_percent"
    assert (
        COMMISSION_FALLBACK_CHAIN[1] == "platform_settings.default_commission_percent"
    )
    assert COMMISSION_FALLBACK_CHAIN[2] == Decimal("0.0100")


def test_search_vector_sync_limit():
    assert SEARCH_VECTOR_SYNC_LIMIT == 1000


def test_gateway_denylist():
    assert "webhook_secret" in GATEWAY_RESPONSE_DENYLIST
    assert "credentials_encrypted" in GATEWAY_RESPONSE_DENYLIST
