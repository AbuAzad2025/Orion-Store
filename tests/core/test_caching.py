"""Phase 14 catalog caching tests."""

from __future__ import annotations

import json

from core.caching import (
    cache_get_json,
    cache_set_json,
    invalidate_tenant_catalog,
    read_through_json,
    store_product_detail_key,
)


class _FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    @property
    def available(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def incr(self, key: str) -> int:
        current = int(self._data.get(key, "0"))
        current += 1
        self._data[key] = str(current)
        return current


def _enable_cache(app):
    app.config["TESTING"] = False
    app.config["CACHE_ENABLED"] = True
    app.extensions["redis_cache"] = _FakeRedis()


def test_cache_disabled_during_pytest(app):
    assert cache_get_json("missing") is None


def test_read_through_json_hits_cache_once(app):
    _enable_cache(app)
    calls: list[int] = []

    with app.app_context():

        def factory():
            calls.append(1)
            return {"ok": True}

        assert read_through_json("demo:key", factory) == {"ok": True}
        assert read_through_json("demo:key", factory) == {"ok": True}
        assert len(calls) == 1


def test_invalidate_bumps_catalog_version(app):
    _enable_cache(app)
    with app.app_context():
        key_v1 = store_product_detail_key(5, "widget", "ar")
        cache_set_json(key_v1, {"product": {"slug": "widget"}})
        invalidate_tenant_catalog(5)
        key_v2 = store_product_detail_key(5, "widget", "ar")
        assert key_v1 != key_v2
        assert cache_get_json(key_v1) == {"product": {"slug": "widget"}}
        assert cache_get_json(key_v2) is None


def test_cache_set_get_roundtrip(app):
    _enable_cache(app)
    with app.app_context():
        cache_set_json("k", {"n": 1})
        raw = app.extensions["redis_cache"].get("k")
        assert json.loads(raw) == {"n": 1}
        assert cache_get_json("k") == {"n": 1}
