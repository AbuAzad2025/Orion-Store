"""Live FX provider: validation, cache, parsing and failure paths."""

from __future__ import annotations

from decimal import Decimal

import pytest

import currency_svc.exchange_rate_provider as provider


@pytest.fixture(autouse=True)
def clear_cache():
    provider._CACHE.clear()
    yield
    provider._CACHE.clear()


class _Response:
    def __init__(self, payload: dict, fail: bool = False):
        self._payload = payload
        self._fail = fail

    def raise_for_status(self):
        if self._fail:
            raise provider.requests.HTTPError("bad status")

    def json(self):
        return self._payload


def test_invalid_codes_return_none():
    assert provider.fetch_live_rate("ILS", "US") is None
    assert provider.fetch_live_rate("", "USD") is None
    assert provider.fetch_live_rate("ILS", None) is None


def test_same_currency_is_one_without_network():
    assert provider.fetch_live_rate("ILS", "ils") == Decimal(1)
    assert not provider._CACHE


def test_cache_hit_skips_network(monkeypatch):
    provider._CACHE["ILS:EUR"] = (provider.time.time(), Decimal("0.27"))

    def boom(*args, **kwargs):
        raise AssertionError("network must not be called on a cache hit")

    monkeypatch.setattr(provider.requests, "get", boom)
    assert provider.fetch_live_rate("ils", "eur") == Decimal("0.27")


def test_successful_fetch_is_parsed_and_cached(monkeypatch):
    seen = {}

    def fake_get(url, timeout):
        seen["url"] = url
        seen["timeout"] = timeout
        return _Response({"rates": {"EUR": 0.273177, "USD": 1.0}})

    monkeypatch.setattr(provider.requests, "get", fake_get)
    rate = provider.fetch_live_rate("ILS", "EUR")

    assert rate == Decimal("0.273177")
    assert seen["url"] == provider.DEFAULT_URL.format(base="ILS")
    assert seen["timeout"] == 6
    assert "ILS:EUR" in provider._CACHE


def test_missing_quote_returns_none(monkeypatch):
    monkeypatch.setattr(
        provider.requests, "get", lambda *a, **k: _Response({"rates": {"USD": 1.0}})
    )
    assert provider.fetch_live_rate("ILS", "EUR") is None


def test_non_positive_rate_returns_none(monkeypatch):
    monkeypatch.setattr(
        provider.requests, "get", lambda *a, **k: _Response({"rates": {"EUR": 0}})
    )
    assert provider.fetch_live_rate("ILS", "EUR") is None


def test_missing_rates_payload_returns_none(monkeypatch):
    monkeypatch.setattr(provider.requests, "get", lambda *a, **k: _Response({}))
    assert provider.fetch_live_rate("ILS", "EUR") is None


def test_http_error_returns_none(monkeypatch):
    monkeypatch.setattr(
        provider.requests, "get", lambda *a, **k: _Response({}, fail=True)
    )
    assert provider.fetch_live_rate("ILS", "EUR") is None


def test_invalid_number_returns_none(monkeypatch):
    monkeypatch.setattr(
        provider.requests, "get", lambda *a, **k: _Response({"rates": {"EUR": "abc"}})
    )
    assert provider.fetch_live_rate("ILS", "EUR") is None


def test_timeout_exception_returns_none(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise provider.requests.Timeout("slow")

    monkeypatch.setattr(provider.requests, "get", raise_timeout)
    assert provider.fetch_live_rate("ILS", "EUR") is None
