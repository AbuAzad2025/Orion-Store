#!/usr/bin/env python3
"""Fail-closed integration readiness report (configuration surface only).

No provider HTTP calls, no database access, no credential decryption. Every
missing environment variable is reported by name; secret values are never
printed, logged or compared. Default posture is ``whatsapp_only``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

PAYMENT_SHARED_ENV: tuple[str, ...] = (
    "PAYMENT_LIVE_CALLS_ENABLED",
    "PAYMENT_STUB_ALLOWED",
    "ENCRYPTION_KEY",
    "WEBHOOK_SECRET",
)
PAYMENT_ENDPOINT_ENV: dict[str, str] = {
    "paypal": "PAYPAL_API_BASE_URL",
    "palpay": "PALPAY_API_BASE_URL",
    "bnpl": "BNPL_API_BASE_URL",
}
ADAPTERS: tuple[str, ...] = ("stripe", "paypal", "palpay", "bnpl_tabby", "bnpl_tamara")
SMTP_BASE_ENV: tuple[str, ...] = ("SMTP_HOST", "SMTP_PORT", "SMTP_FROM")
SMTP_AUTH_ENV: tuple[str, ...] = ("SMTP_USER", "SMTP_PASSWORD")


def _present(environ: Mapping[str, str], key: str) -> bool:
    return bool(str(environ.get(key, "") or "").strip())


def _missing(environ: Mapping[str, str], keys: Sequence[str]) -> list[str]:
    return [key for key in keys if not _present(environ, key)]


def collect_report(
    environ: Mapping[str, str] | None = None,
    *,
    require_payment: bool = False,
    require_smtp: bool = False,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    whatsapp = {
        "status": "ready",
        "env_required": [],
        "note": "wa.me deep links; no API, no credentials, no env",
    }
    payment_missing = _missing(env, PAYMENT_SHARED_ENV)
    payment_declared = any(_present(env, k) for k in PAYMENT_SHARED_ENV) or any(
        _present(env, k) for k in PAYMENT_ENDPOINT_ENV.values()
    )
    payment_required = payment_declared or require_payment
    payment_status = (
        "not_ready"
        if payment_missing and payment_required
        else "ready" if not payment_missing else "skipped"
    )
    optional_unset = [k for k in PAYMENT_ENDPOINT_ENV.values() if not _present(env, k)]
    adapters = {
        name: {
            "status": "env_ready" if not payment_missing else "not_ready",
            "missing": list(payment_missing),
            "credentials": "encrypted in DB; not inspected",
            "live_calls_made": False,
        }
        for name in ADAPTERS
    }
    payment = {
        "status": payment_status,
        "declared": payment_declared,
        "required": payment_required,
        "missing": payment_missing,
        "reason": "missing_env" if payment_missing else None,
        "optional_unset": optional_unset,
        "adapters": adapters,
        "credentials_read": False,
        "live_calls_made": False,
    }
    smtp_missing = _missing(env, SMTP_BASE_ENV)
    smtp_declared = any(_present(env, k) for k in (*SMTP_BASE_ENV, *SMTP_AUTH_ENV))
    smtp_required = smtp_declared or require_smtp
    user_present = _present(env, "SMTP_USER")
    password_present = _present(env, "SMTP_PASSWORD")
    smtp_auth_missing: list[str] = []
    if user_present != password_present:
        smtp_auth_missing = ["SMTP_PASSWORD"] if user_present else ["SMTP_USER"]
    smtp_problem = bool(smtp_missing) or bool(smtp_auth_missing)
    smtp_status = (
        "not_ready"
        if smtp_problem and smtp_required
        else "ready" if not smtp_problem else "skipped"
    )
    smtp = {
        "status": smtp_status,
        "declared": smtp_declared,
        "required": smtp_required,
        "missing": smtp_missing,
        "missing_auth": smtp_auth_missing,
        "reason": (
            "missing_env"
            if smtp_missing
            else "partial_auth" if smtp_auth_missing else None
        ),
        "live_calls_made": False,
    }
    go = payment_status != "not_ready" and smtp_status != "not_ready"
    return {
        "operating_model": "whatsapp_only",
        "status": "ready" if go else "not_ready",
        "go": go,
        "no_live_calls": True,
        "credentials_read": False,
        "whatsapp": whatsapp,
        "payment": payment,
        "smtp": smtp,
    }


def _print_report(report: dict[str, Any]) -> None:
    print("Orion integration readiness (env-only; no live calls, no credentials)")
    print(f"Operating model: {report['operating_model']}")
    wa = report["whatsapp"]
    print(f"WhatsApp ordering: {wa['status']} (env_required={wa['env_required']})")
    for label, key in (("Payment", "payment"), ("SMTP", "smtp")):
        part = report[key]
        print(f"{label}: {part['status']} (required={part['required']})")
        for name in part["missing"]:
            print(f"  MISSING {name}")
        for name in part.get("missing_auth", []):
            print(f"  MISSING_AUTH {name}")
        if part.get("reason"):
            print(f"  REASON {part['reason']}")
    for name in report["payment"]["optional_unset"]:
        print(f"  OPTIONAL_UNSET {name}")
    print(f"RESULT: {'GO' if report['go'] else 'NO-GO'}")


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--require-payment", action="store_true")
    parser.add_argument("--require-smtp", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    report = collect_report(
        environ,
        require_payment=args.require_payment or args.strict,
        require_smtp=args.require_smtp or args.strict,
    )
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report["go"] else 1


if __name__ == "__main__":
    sys.exit(main())
