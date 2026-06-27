"""Sentry + Prometheus hooks (§18, phase 14)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from flask import Flask, Response, g, request

from core.logging_config import configure_logging

if TYPE_CHECKING:
    from prometheus_client import Counter, Histogram

_REQUEST_COUNT: Counter | None = None
_REQUEST_LATENCY: Histogram | None = None


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
    global _REQUEST_COUNT, _REQUEST_LATENCY
    if app.config.get("TESTING") or not app.config.get("PROMETHEUS_ENABLED", True):
        return

    from prometheus_client import Counter, Histogram, generate_latest

    _REQUEST_COUNT = Counter(
        "orion_http_requests_total",
        "HTTP requests",
        ["method", "endpoint", "status"],
    )
    _REQUEST_LATENCY = Histogram(
        "orion_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "endpoint"],
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
        return Response(
            generate_latest(),
            mimetype="text/plain; version=0.0.4; charset=utf-8",
        )


def register_monitoring(app: Flask) -> None:
    configure_logging(app)
    init_sentry(app)
    init_prometheus(app)
