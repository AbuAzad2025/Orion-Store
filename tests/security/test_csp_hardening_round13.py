"""Round-13 CSP hardening: deny-by-default directives + Permissions-Policy."""

from __future__ import annotations

import re
from pathlib import Path

from flask import Flask, Response, g

from core.security_headers import PERMISSIONS_POLICY, register_security_headers

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIRS = (
    ROOT / "06-STOREFRONT" / "themes" / "default" / "templates",
    ROOT / "07-ADMIN" / "templates",
)
NONCE_RE = re.compile(r"script-src 'self' 'nonce-([A-Za-z0-9_-]+)'")


def _directives(csp: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in csp.split(";"):
        parts = item.strip().split(None, 1)
        if len(parts) == 2:
            parsed[parts[0]] = parts[1]
    return parsed


def _nonce(csp: str) -> str:
    match = NONCE_RE.search(csp)
    assert match is not None, f"script-src nonce missing: {csp}"
    return match.group(1)


def test_csp_hardening_directives(app) -> None:
    with app.test_client() as client:
        csp = client.get("/health").headers["Content-Security-Policy"]
    d = _directives(csp)
    assert d["default-src"] == "'self'"
    assert d["img-src"] == "'self' data: https:"
    assert d["script-src"].startswith("'self' 'nonce-")
    assert d["style-src"].startswith("'self' 'nonce-")
    assert d["frame-ancestors"] == "'none'"
    assert d["object-src"] == "'none'"
    assert d["base-uri"] == "'self'"
    assert d["form-action"] == "'self'"


def test_csp_nonce_is_per_request_and_no_unsafe_inline(app) -> None:
    with app.test_client() as client:
        first = client.get("/health").headers["Content-Security-Policy"]
        second = client.get("/health").headers["Content-Security-Policy"]
    assert "'unsafe-inline'" not in first
    assert "'unsafe-inline'" not in second
    assert _nonce(first) != _nonce(second)


def test_permissions_policy_header(app) -> None:
    with app.test_client() as client:
        policy = client.get("/health").headers["Permissions-Policy"]
    assert policy == PERMISSIONS_POLICY
    for feature in ("camera", "geolocation", "microphone", "payment", "usb"):
        assert f"{feature}=()" in policy
    assert "*" not in policy


def test_rendered_inline_script_nonce_matches_header() -> None:
    probe = Flask(__name__)

    @probe.get("/nonce-page")
    def nonce_page() -> Response:
        return Response(f'<script nonce="{g.csp_nonce}">window.ok=1</script>')

    register_security_headers(probe)
    with probe.test_client() as client:
        resp = client.get("/nonce-page")
    nonce = _nonce(resp.headers["Content-Security-Policy"])
    assert f'<script nonce="{nonce}">' in resp.get_data(as_text=True)


def test_templates_have_no_tags_conflicting_with_new_directives() -> None:
    forbidden = re.compile(r"<(base|object|embed|applet)\b", re.IGNORECASE)
    offenders: list[str] = []
    for directory in TEMPLATE_DIRS:
        for template in directory.rglob("*.html"):
            if forbidden.search(template.read_text(encoding="utf-8")):
                offenders.append(str(template.relative_to(ROOT)))
    assert offenders == [], f"Templates incompatible with tightened CSP: {offenders}"
