"""Round-14 regression: integration readiness is fail-closed and explicit."""

from __future__ import annotations

import json

from scripts.check_integration_readiness import (
    ADAPTERS,
    PAYMENT_SHARED_ENV,
    SMTP_BASE_ENV,
    collect_report,
    main,
)

FULL_PAYMENT_ENV = {key: "set" for key in PAYMENT_SHARED_ENV}
FULL_SMTP_ENV = {key: "set" for key in SMTP_BASE_ENV}
SECRET = "super-secret-value-must-never-appear"


def test_empty_env_is_whatsapp_only_and_names_every_missing_env():
    report = collect_report({})
    assert report["operating_model"] == "whatsapp_only"
    assert report["whatsapp"]["status"] == "ready"
    assert report["payment"]["status"] == "skipped"
    assert report["smtp"]["status"] == "skipped"
    assert report["payment"]["missing"] == list(PAYMENT_SHARED_ENV)
    assert report["smtp"]["missing"] == list(SMTP_BASE_ENV)
    assert report["go"] is True


def test_declared_payment_fails_closed():
    report = collect_report({"PAYMENT_LIVE_CALLS_ENABLED": "true"})
    payment = report["payment"]
    assert payment["declared"] is True
    assert payment["status"] == "not_ready"
    assert set(payment["adapters"]) == set(ADAPTERS)
    assert report["go"] is False


def test_require_flags_fail_closed_on_empty_env():
    assert collect_report({}, require_payment=True)["payment"]["status"] == "not_ready"
    smtp = collect_report({}, require_smtp=True)["smtp"]
    assert smtp["status"] == "not_ready"
    assert "SMTP_PASSWORD" not in smtp["missing"]


def test_partial_smtp_auth_is_reported_explicitly():
    env = dict(FULL_SMTP_ENV, SMTP_USER="user@example.test")
    smtp = collect_report(env, require_smtp=True)["smtp"]
    assert smtp["status"] == "not_ready"
    assert smtp["missing_auth"] == ["SMTP_PASSWORD"]


def test_fully_configured_integrations_are_ready():
    env = dict(FULL_PAYMENT_ENV)
    env.update(FULL_SMTP_ENV)
    report = collect_report(env, require_payment=True, require_smtp=True)
    assert report["payment"]["status"] == "ready"
    assert report["smtp"]["status"] == "ready"
    assert report["go"] is True


def test_report_never_contains_secret_values():
    env = dict(FULL_PAYMENT_ENV)
    env.update(FULL_SMTP_ENV)
    for key in ("SMTP_PASSWORD", "SMTP_USER", "ENCRYPTION_KEY", "WEBHOOK_SECRET"):
        env[key] = SECRET
    assert SECRET not in json.dumps(
        collect_report(env, require_payment=True, require_smtp=True)
    )


def test_cli_prints_missing_names_and_returns_one(capsys):
    assert main(["--require-smtp"], environ={}) == 1
    out = capsys.readouterr().out
    for key in SMTP_BASE_ENV:
        assert f"MISSING {key}" in out
    assert "NO-GO" in out
