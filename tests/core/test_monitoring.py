"""Phase 14 monitoring — logging, readiness, Prometheus."""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

from core.logging_config import JsonLogFormatter, configure_logging
from core.monitoring import init_prometheus, init_sentry, register_monitoring


def test_json_log_formatter():
    record = logging.LogRecord(
        name="orion",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    line = JsonLogFormatter().format(record)
    payload = json.loads(line)
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"


def test_configure_logging(app):
    app.config["LOG_JSON"] = True
    configure_logging(app)
    assert app.logger.level == logging.INFO


def test_init_sentry_skips_without_dsn(app):
    app.config["TESTING"] = False
    app.config["SENTRY_DSN"] = ""
    init_sentry(app)


def test_init_sentry_with_dsn(app):
    app.config["TESTING"] = False
    app.config["SENTRY_DSN"] = "https://example@o0.ingest.sentry.io/0"
    with patch("sentry_sdk.init") as mock_init:
        init_sentry(app)
        mock_init.assert_called_once()


def test_register_monitoring_in_testing(app):
    register_monitoring(app)


def test_ready_endpoint_ok(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"
    assert data["database"] is True


def test_metrics_not_exposed_in_testing(client):
    response = client.get("/metrics")
    assert response.status_code == 404


def test_prometheus_metrics_when_enabled():
    from flask import Flask

    from core.monitoring import init_prometheus

    app = Flask(__name__)
    app.config["TESTING"] = False
    app.config["PROMETHEUS_ENABLED"] = True

    @app.get("/health")
    def health():
        return "ok", 200

    init_prometheus(app)
    with app.test_client() as client:
        client.get("/health")
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert b"orion_http_requests_total" in metrics.data
