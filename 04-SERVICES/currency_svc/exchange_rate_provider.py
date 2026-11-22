"""Live FX rate provider (exchangerate-api open endpoint, no API key).

Fetched rates are cached in-process for a short TTL and persisted by
CurrencyService into ``currency_rates`` as a durable offline fallback.
"""

from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation

import requests

DEFAULT_URL = "https://open.er-api.com/v6/latest/{base}"
_CACHE: dict[str, tuple[float, Decimal]] = {}
_CACHE_TTL = 1800  # seconds


def fetch_live_rate(
    base: str, quote: str, url_template: str = DEFAULT_URL
) -> Decimal | None:
    base = (base or "").strip().upper()
    quote = (quote or "").strip().upper()
    if len(base) != 3 or len(quote) != 3:
        return None
    if base == quote:
        return Decimal(1)

    key = f"{base}:{quote}"
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    try:
        response = requests.get(url_template.format(base=base), timeout=6)
        response.raise_for_status()
        payload = response.json()
        rates = payload.get("rates") or {}
        if quote not in rates:
            return None
        rate = Decimal(str(rates[quote]))
        if rate <= 0:
            return None
        _CACHE[key] = (time.time(), rate)
        return rate
    except (
        requests.RequestException,
        ValueError,
        KeyError,
        InvalidOperation,
        TypeError,
    ):
        return None
