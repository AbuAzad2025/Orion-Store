"""Theme resolution and rendering (wave 5 #57)."""

from __future__ import annotations

from flask import render_template

from core.context import get_locale


class ThemeEngine:
    def render(self, template_name: str, **context):
        # Routes pass `locale` explicitly; keep a request-scoped fallback so a
        # future template render can never lose the html lang/dir wiring.
        context.setdefault("locale", get_locale())
        return render_template(template_name, **context)
