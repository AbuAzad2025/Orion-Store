"""Theme resolution and rendering (wave 5 #57)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import has_request_context, render_template, request

from core.context import get_locale
from engine.ui_text import translate

SUPPORTED_CURRENCIES = frozenset({"ILS", "USD", "EUR", "GBP", "SAR", "AED", "JOD"})


def _format_money(value, source: str, target: str) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    if source == target:
        return f"{amount:.2f}"
    from currency_svc.currency_service import CurrencyService

    try:
        converted = CurrencyService().convert(
            amount=amount, from_currency=source, to_currency=target
        )
    except Exception:
        return f"{amount:.2f}"
    return f"{converted:.2f}"


class ThemeEngine:
    def render(self, template_name: str, **context):
        # Routes pass `locale` explicitly; keep a request-scoped fallback so a
        # future template render can never lose the html lang/dir wiring.
        locale = context.setdefault("locale", get_locale())
        tenant = context.get("tenant")
        source_currency = (
            (getattr(tenant, "default_currency", None) or "ILS")
            if tenant is not None
            else "ILS"
        )
        selected = ""
        if has_request_context():
            selected = (request.args.get("currency") or "").strip().upper()
        context["currency"] = (
            selected if selected in SUPPORTED_CURRENCIES else source_currency
        )
        context["t"] = lambda key: translate(key, locale)
        context["money"] = lambda value: _format_money(
            value, source_currency, context["currency"]
        )
        context["currencies"] = sorted(SUPPORTED_CURRENCIES)
        if "cookie_settings" not in context and tenant is not None:
            from compliance.compliance import CookieConsentSetting

            context["cookie_settings"] = CookieConsentSetting.query.filter_by(
                tenant_id=tenant.id
            ).first()
        return render_template(template_name, **context)
