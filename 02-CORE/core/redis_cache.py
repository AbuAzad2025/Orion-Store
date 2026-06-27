"""Redis cache boundary with graceful fallback (§18, MVP hardening)."""

from __future__ import annotations

from typing import Any


def ping_redis(redis_url: str | None) -> bool:
    if not redis_url:
        return False
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        return False


class RedisCache:
    """Thin Redis wrapper — no-op when Redis is unavailable."""

    def __init__(self, redis_url: str | None) -> None:
        self._client: Any = None
        if redis_url:
            try:
                import redis

                self._client = redis.from_url(redis_url, decode_responses=True)
                self._client.ping()
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> str | None:
        if not self._client:
            return None
        return self._client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        if not self._client:
            return
        self._client.setex(key, ttl_seconds, value)

    def delete(self, key: str) -> None:
        if not self._client:
            return
        self._client.delete(key)
