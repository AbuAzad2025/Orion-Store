"""Staging stack config smoke tests (§18)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "01-FOUNDATION" / "infrastructure"
STAGING = ROOT / "01-FOUNDATION" / "staging"


def test_staging_compose_declares_core_services():
    text = (INFRA / "docker-compose.staging.yml").read_text(encoding="utf-8")
    for name in ("orion-api", "postgres", "redis", "prometheus", "grafana"):
        assert name in text


def test_dockerfile_runs_gunicorn_entrypoint():
    dockerfile = (INFRA / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (INFRA / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "gunicorn" in dockerfile
    assert "flask db upgrade" in entrypoint


def test_prometheus_scrapes_orion_service():
    prom = (STAGING / "prometheus.yml").read_text(encoding="utf-8")
    assert "orion-api:5000" in prom
    assert "/etc/prometheus/alerts" in prom


def test_grafana_dashboard_is_valid_json():
    dashboard = STAGING / "grafana" / "dashboards" / "orion-overview.json"
    payload = json.loads(dashboard.read_text(encoding="utf-8"))
    assert payload["title"] == "Orion API Overview"
    assert payload["panels"]
