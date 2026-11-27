"""Security response headers with a per-request CSP nonce (§0.5)."""

from __future__ import annotations

import secrets

from flask import Flask, Response, g


def register_security_headers(app: Flask) -> None:
    @app.before_request
    def _issue_csp_nonce() -> None:
        g.csp_nonce = secrets.token_urlsafe(18)

    @app.context_processor
    def _inject_csp_nonce() -> dict[str, str]:
        return {"csp_nonce": getattr(g, "csp_nonce", "")}

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        nonce = getattr(g, "csp_nonce", "")
        # CSP_ALLOW_UNSAFE_INLINE is a legacy rollback switch only; no inline
        # scripts/styles/style attributes remain in the codebase.
        unsafe = " 'unsafe-inline'" if app.config.get("CSP_ALLOW_UNSAFE_INLINE") else ""
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'{unsafe}; "
            f"style-src 'self' 'nonce-{nonce}'{unsafe}; "
            "img-src 'self' data: https:;"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        if app.config.get("ENFORCE_HSTS"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
