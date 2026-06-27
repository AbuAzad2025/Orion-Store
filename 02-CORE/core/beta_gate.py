"""Closed-beta tenant allowlist (§18 phase 14)."""

from __future__ import annotations

from core.exceptions import AuthorizationError


def _config(name: str, default=None):
    try:
        from flask import current_app

        return current_app.config.get(name, default)
    except RuntimeError:
        return default


def beta_mode_enabled() -> bool:
    if _config("TESTING", False):
        return False
    return bool(_config("BETA_MODE", False))


def beta_allowlist() -> set[str]:
    raw = str(_config("BETA_TENANT_SLUGS", "") or "")
    return {slug.strip() for slug in raw.split(",") if slug.strip()}


def is_tenant_beta_allowed(tenant_slug: str | None) -> bool:
    if not beta_mode_enabled():
        return True
    if not tenant_slug:
        return True
    return tenant_slug in beta_allowlist()


def enforce_beta_tenant_access(tenant_slug: str | None) -> None:
    if not is_tenant_beta_allowed(tenant_slug):
        raise AuthorizationError("This store is not in the closed beta program.")


def is_beta_gated_path(path: str) -> bool:
    if path in ("/health", "/ready", "/metrics", "/webhooks/status"):
        return False
    if path.startswith("/admin") or path.startswith("/api/v1/platform"):
        return False
    if path.startswith("/api/v1/auth") or path.startswith("/webhooks/"):
        return False
    if path.startswith("/api/v1/store") or path.startswith("/store/static"):
        return True
    if path.startswith("/api/"):
        return False
    return not path.startswith("/api")
