"""Theme resolution and rendering (wave 5 #57)."""

from __future__ import annotations

from flask import render_template

from core.context import get_locale


class ThemeEngine:
    def render(self, template_name: str, **context):
        # Routes pass `locale` explicitly; keep a request-scoped fallback so a
        # future template render can never lose the html lang/dir wiring.
        context.setdefault("locale", get_locale())
        if "cookie_settings" not in context:
            tenant = context.get("tenant")
            if tenant is not None:
                from compliance.compliance import CookieConsentSetting

                context["cookie_settings"] = CookieConsentSetting.query.filter_by(
                    tenant_id=tenant.id
                ).first()
        return render_template(template_name, **context)
