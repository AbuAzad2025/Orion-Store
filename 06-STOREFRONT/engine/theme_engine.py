"""Theme resolution and rendering (wave 5 #57)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import current_app, has_request_context, render_template, request

from core.context import get_locale
from engine.ui_text import translate

SUPPORTED_CURRENCIES = frozenset({"ILS", "USD", "EUR", "GBP", "SAR", "AED", "JOD"})


def _format_money(value, source: str, target: str, markup_percent: float = 0) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    if source == target:
        return f"{amount:.2f}"
    from currency_svc.currency_service import CurrencyService

    try:
        converted = CurrencyService().convert(
            amount=amount,
            from_currency=source,
            to_currency=target,
            markup_percent=markup_percent,
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
        from currency_svc.currency_service import CurrencyService

        markup = float(current_app.config.get("CURRENCY_FX_MARKUP_PERCENT", 0))
        context["fx_markup_percent"] = markup
        context["fx_rate_info"] = CurrencyService().rate_info(
            source_currency, context["currency"]
        )
        context["t"] = lambda key: translate(key, locale)
        if tenant is not None and has_request_context():
            base = request.host_url.rstrip("/")
            path = request.path or ""
            slug = tenant.slug
            if path == "/":
                clean = f"/s/{slug}/"
            elif path.startswith(("/product/", "/category/")):
                clean = f"/s/{slug}{path}"
            else:
                clean = path
            context.setdefault("canonical_url", base + clean)
            context.setdefault(
                "meta_description",
                f"{tenant.name_for(locale)} — " + translate("hero_subtitle", locale),
            )
            context.setdefault(
                "structured_data",
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": tenant.name_for(locale),
                    "url": base + f"/s/{slug}/",
                },
            )
        context["money"] = lambda value: _format_money(
            value, source_currency, context["currency"], markup
        )
        from core.store_token import issue as issue_store_token

        context["store_token"] = issue_store_token(tenant) if tenant else ""
        # Professional WhatsApp order text with signed-in customer details.
        from flask import g

        from engine.whatsapp import (
            format_bundle_order,
            format_product_order,
            format_store_inquiry,
        )

        order_customer = getattr(g, "user", None) if has_request_context() else None
        order_store = tenant.name_for(locale) if tenant is not None else ""
        context["product_order_text"] = lambda name, price, qty=1: format_product_order(
            order_store, name, price, context["currency"], order_customer, locale, qty
        )
        context["bundle_order_text"] = lambda name, price: format_bundle_order(
            order_store, name, price, context["currency"], order_customer, locale
        )
        context["store_inquiry_text"] = lambda: format_store_inquiry(
            order_store, order_customer, locale
        )
        from urllib.parse import urlencode

        context["keep_q"] = (
            "".join(
                "&" + urlencode({key: value})
                for key, value in request.args.items()
                if key not in ("locale", "currency", "store")
            )
            if has_request_context()
            else ""
        )
        context["currencies"] = sorted(SUPPORTED_CURRENCIES)
        if "cookie_settings" not in context and tenant is not None:
            from compliance.compliance import CookieConsentSetting

            context["cookie_settings"] = CookieConsentSetting.query.filter_by(
                tenant_id=tenant.id
            ).first()
        return render_template(template_name, **context)
