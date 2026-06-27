"""Catalog cache keys and read-through helpers (§18, phase 14)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from core.redis_cache import RedisCache


def _app_config(name: str, default: Any = None) -> Any:
    try:
        from flask import current_app

        return current_app.config.get(name, default)
    except RuntimeError:
        return default


def cache_enabled() -> bool:
    if _app_config("TESTING", False):
        return False
    return bool(_app_config("CACHE_ENABLED", True))


def get_cache() -> RedisCache | None:
    try:
        from flask import current_app

        cache = current_app.extensions.get("redis_cache")
    except RuntimeError:
        return None
    if not cache or not getattr(cache, "available", False):
        return None
    return cache


def cache_ttl_seconds() -> int:
    return int(_app_config("CACHE_TTL_SECONDS", 300))


def catalog_version_key(tenant_id: int) -> str:
    return f"catalog:{tenant_id}:ver"


def get_catalog_version(tenant_id: int) -> int:
    cache = get_cache()
    if not cache or not cache_enabled():
        return 0
    raw = cache.get(catalog_version_key(tenant_id))
    return int(raw) if raw else 0


def invalidate_tenant_catalog(tenant_id: int) -> None:
    """Bump version — stale storefront keys expire via TTL."""
    cache = get_cache()
    if not cache or not cache_enabled():
        return
    cache.incr(catalog_version_key(tenant_id))


def store_products_list_key(
    tenant_id: int, page: int, per_page: int, locale: str
) -> str:
    version = get_catalog_version(tenant_id)
    return f"store:{tenant_id}:v{version}:products:{page}:{per_page}:{locale}"


def store_product_detail_key(tenant_id: int, slug: str, locale: str) -> str:
    version = get_catalog_version(tenant_id)
    return f"store:{tenant_id}:v{version}:product:{slug}:{locale}"


def store_categories_list_key(
    tenant_id: int, page: int, per_page: int, locale: str
) -> str:
    version = get_catalog_version(tenant_id)
    return f"store:{tenant_id}:v{version}:categories:{page}:{per_page}:{locale}"


def cache_get_json(key: str) -> Any | None:
    if not cache_enabled():
        return None
    cache = get_cache()
    if not cache:
        return None
    raw = cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cache.delete(key)
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    if not cache_enabled():
        return
    cache = get_cache()
    if not cache:
        return
    ttl = ttl_seconds if ttl_seconds is not None else cache_ttl_seconds()
    cache.set(key, json.dumps(value, ensure_ascii=False), ttl_seconds=ttl)


def read_through_json(key: str, factory: Callable[[], dict]) -> dict:
    cached = cache_get_json(key)
    if cached is not None:
        return cached
    payload = factory()
    cache_set_json(key, payload)
    return payload
