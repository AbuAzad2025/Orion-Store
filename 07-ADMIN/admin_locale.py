"""Locale helpers for the Flask admin dashboards (Arabic / English)."""

from __future__ import annotations

from flask import request

SUPPORTED_LOCALES = ("ar", "en")
ADMIN_LOCALE_COOKIE = "orion_admin_locale"


def _normalize_locale(value):
    """Return a supported locale code (``ar``/``en``) or ``None``."""
    if not value:
        return None
    code = str(value).strip().lower()
    for separator in ("-", "_"):
        code = code.split(separator)[0]
    return code if code in SUPPORTED_LOCALES else None


def get_admin_locale():
    """Resolve the admin UI locale.

    Resolution order: ``?locale=`` query string, ``orion_admin_locale``
    cookie, ``X-Locale`` header, then Arabic as the default.
    """
    for candidate in (
        request.args.get("locale"),
        request.cookies.get(ADMIN_LOCALE_COOKIE),
        request.headers.get("X-Locale"),
    ):
        locale = _normalize_locale(candidate)
        if locale:
            return locale
    return "ar"


def t(ar, en, locale=None):
    """Return the Arabic or English string for the resolved admin locale."""
    if locale is None:
        current = get_admin_locale()
    else:
        current = _normalize_locale(locale) or "ar"
    return en if current == "en" else ar


def remember_admin_locale(response):
    """Persist the locale chosen via ``?locale=`` in a long-lived cookie."""
    current = get_admin_locale()
    if request.cookies.get(ADMIN_LOCALE_COOKIE) != current:
        response.set_cookie(
            ADMIN_LOCALE_COOKIE,
            current,
            max_age=60 * 60 * 24 * 365,
            samesite="Lax",
        )
    return response
