"""Security response headers (§0.5)."""

from __future__ import annotations

from flask import Flask, Response


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; script-src 'self' 'unsafe-inline' "
                "https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' "
                "https://cdn.tailwindcss.com; img-src 'self' data:;"
            ),
        )
        if app.config.get("ENFORCE_HSTS"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
