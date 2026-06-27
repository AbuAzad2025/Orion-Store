"""MVP hardening — rate limit, Redis cache, health."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.rate_limit import init_rate_limiter
from core.redis_cache import RedisCache, ping_redis


def test_ping_redis_without_url():
    assert ping_redis(None) is False
    assert ping_redis("") is False


def test_ping_redis_unreachable():
    assert ping_redis("redis://127.0.0.1:1") is False


def test_redis_cache_noop_without_server():
    cache = RedisCache("redis://127.0.0.1:1")
    assert cache.available is False
    assert cache.get("k") is None
    cache.set("k", "v")
    cache.delete("k")


def test_redis_cache_roundtrip():
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = "hello"
    with patch("redis.from_url", return_value=mock_client):
        cache = RedisCache("redis://localhost:6379/0")
    assert cache.available is True
    assert cache.get("k") == "hello"
    cache.set("k", "v", ttl_seconds=60)
    mock_client.setex.assert_called_once_with("k", 60, "v")
    cache.delete("k")
    mock_client.delete.assert_called_once_with("k")


def test_init_rate_limiter_testing_uses_memory(app):
    app.config["TESTING"] = True
    init_rate_limiter(app)
    assert app.config["RATELIMIT_ENABLED"] is False


def test_health_includes_redis_flag(client):
    response = client.get("/health")
    data = response.get_json()
    assert response.status_code == 200
    assert "redis" in data
    assert isinstance(data["redis"], bool)
