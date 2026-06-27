"""Theme resolution and rendering (wave 5 #57)."""

from __future__ import annotations

from flask import render_template


class ThemeEngine:
    def render(self, template_name: str, **context):
        return render_template(template_name, **context)
