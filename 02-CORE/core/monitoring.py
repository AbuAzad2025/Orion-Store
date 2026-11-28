"""Sentry + Prometheus hooks (§18, phase 14)."""

from __future__ import annotations

import hmac
import json
import math
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import Flask, Response, current_app, g, request

from core.logging_config import configure_logging

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from prometheus_client import Counter, Histogram

_REQUEST_COUNT: Counter | None = None
_REQUEST_LATENCY: Histogram | None = None
_REGISTRY: Any = None
_CELERY_UP: Any = None
_CELERY_AGE: Any = None
_CELERY_QUEUE: Any = None


def _cfg(name: str, default: Any) -> Any:
    try:
        return current_app.config.get(name, default)
    except RuntimeError:
        return os.environ.get(name, default)


def _authorize_metrics() -> None:
    token = str(_cfg("METRICS_TOKEN", "") or "")
    if token:
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + token):
            from core.exceptions import AuthenticationError

            raise AuthenticationError("Metrics bearer token required.")
        return
    if str(_cfg("ENV", "") or "").lower() in ("production", "prod"):
        from core.middleware import require_platform_admin

        require_platform_admin()


def celery_state() -> dict:
    out: dict = {"worker_up": False, "heartbeat_age": None, "queues": {}}
    url = str(
        _cfg("CELERY_BROKER_URL", "")
        or _cfg("REDIS_URL", "")
        or os.environ.get("REDIS_URL", "")
    )
    if not url:
        return out
    key = str(_cfg("CELERY_HEARTBEAT_KEY", "orion:celery:heartbeat"))
    max_age = int(_cfg("CELERY_HEARTBEAT_MAX_AGE_SECONDS", 120))
    queues = [
        q.strip()
        for q in str(_cfg("CELERY_QUEUE_NAMES", "celery")).split(",")
        if q.strip()
    ]
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        raw = client.get(key)
        if raw is not None:
            value = raw.decode() if isinstance(raw, bytes) else raw
            age = max(0.0, time.time() - float(value))
            out["heartbeat_age"] = round(age, 1)
            out["worker_up"] = age <= max_age
        for name in queues:
            out["queues"][name] = int(client.llen(name))
    except Exception:
        return out
    return out


def update_celery_gauges() -> dict:
    state = celery_state()
    if _CELERY_UP is not None:
        _CELERY_UP.set(1 if state["worker_up"] else 0)
    if _CELERY_AGE is not None and state["heartbeat_age"] is not None:
        _CELERY_AGE.set(state["heartbeat_age"])
    if _CELERY_QUEUE is not None:
        for name, depth in state["queues"].items():
            _CELERY_QUEUE.labels(name).set(depth)
    return state


def backup_freshness(path: str, max_age: int) -> tuple[bool, dict]:
    """Fail-closed platform-backup freshness from the JSON heartbeat.

    A store backup must never satisfy the platform gate: the payload's
    ``kind`` must be exactly ``platform``. Only non-secret metadata is read.
    """
    info: dict = {"backup": False}
    if not path:
        return False, info
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return False, info
        kind = str(payload.get("kind", "") or "")
        st = str(payload.get("stamp", "") or "")
        updated = float(payload.get("updated_at", 0) or 0)
    except (OSError, UnicodeError, ValueError, TypeError):
        return False, info
    if not math.isfinite(updated) or updated <= 0:
        return False, info
    info["backup_kind"] = kind
    if st:
        info["backup_stamp"] = st
    age = max(0.0, time.time() - updated)
    info["backup_age_seconds"] = int(age)
    ok = kind == "platform" and bool(st) and age <= max_age
    info["backup"] = ok
    return ok, info


def readiness_dependencies() -> tuple[dict, bool]:
    extra: dict = {}
    failed = False
    if _cfg("READY_REQUIRE_BACKUP", False):
        path = str(_cfg("BACKUP_HEARTBEAT_FILE", "") or "")
        max_age = int(_cfg("BACKUP_HEARTBEAT_MAX_AGE_SECONDS", 172800))
        ok, info = backup_freshness(path, max_age)
        extra.update(info)
        failed = failed or not ok
    if _cfg("READY_REQUIRE_CELERY", False):
        state = update_celery_gauges()
        extra["celery"] = state["worker_up"]
        if state["heartbeat_age"] is not None:
            extra["celery_age_seconds"] = int(state["heartbeat_age"])
        failed = failed or not state["worker_up"]
    return extra, failed


def init_sentry(app: Flask) -> None:
    if app.config.get("TESTING"):
        return
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=app.config.get(
            "SENTRY_ENVIRONMENT", app.config.get("ENV", "development")
        ),
        traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.0)),
    )


def init_prometheus(app: Flask) -> None:
    global _REQUEST_COUNT, _REQUEST_LATENCY, _REGISTRY, _CELERY_UP, _CELERY_AGE, _CELERY_QUEUE
    if app.config.get("TESTING") or not app.config.get("PROMETHEUS_ENABLED", True):
        return

    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    # Private registry per app: re-initialising monitoring (e.g. in tests or
    # multiple app factories) must not re-register global timeseries.
    registry = CollectorRegistry()
    _REGISTRY = registry
    _REQUEST_COUNT = Counter(
        "orion_http_requests_total",
        "HTTP requests",
        ["method", "endpoint", "status"],
        registry=registry,
    )
    _REQUEST_LATENCY = Histogram(
        "orion_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "endpoint"],
        registry=registry,
    )
    _CELERY_UP = Gauge(
        "orion_celery_worker_up", "Celery worker heartbeat fresh", registry=registry
    )
    _CELERY_AGE = Gauge(
        "orion_celery_heartbeat_age_seconds",
        "Seconds since last Celery heartbeat",
        registry=registry,
    )
    _CELERY_QUEUE = Gauge(
        "orion_celery_queue_depth", "Pending Celery tasks", ["queue"], registry=registry
    )

    @app.before_request
    def _prometheus_before() -> None:
        g._orion_request_start = time.perf_counter()

    @app.after_request
    def _prometheus_after(response: Response) -> Response:
        start = getattr(g, "_orion_request_start", None)
        if start is None or _REQUEST_COUNT is None or _REQUEST_LATENCY is None:
            return response
        endpoint = request.endpoint or "unknown"
        elapsed = time.perf_counter() - start
        _REQUEST_LATENCY.labels(request.method, endpoint).observe(elapsed)
        _REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
        return response

    @app.get("/metrics")
    def metrics() -> Response:
        _authorize_metrics()
        if _REGISTRY is not None:
            update_celery_gauges()
        return Response(
            generate_latest(_REGISTRY),
            mimetype="text/plain; version=0.0.4; charset=utf-8",
        )


def register_monitoring(app: Flask) -> None:
    if app.extensions.get("_orion_monitoring_registered"):
        return
    app.extensions["_orion_monitoring_registered"] = True
    configure_logging(app)
    init_sentry(app)
    init_prometheus(app)

    @app.after_request
    def _orion_ready_dependencies(response: Response) -> Response:
        if request.path != "/ready" or response.status_code != 200:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        extra, failed = readiness_dependencies()
        if not extra:
            return response
        payload.update(extra)
        if failed:
            payload["status"] = "not_ready"
            response.status_code = 503
        response.set_data(json.dumps(payload, separators=(",", ":")))
        return response
