"""Store-admin manual order review UI."""

from __future__ import annotations

from pathlib import Path

from admin_locale import get_admin_locale, remember_admin_locale, t
from flask import Blueprint, g, render_template

from platform_svc.platform_settings_service import PlatformSettingsService

_TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
tenant_manual_orders_ui_bp = Blueprint(
    "tenant_manual_orders_ui", __name__, template_folder=str(_TEMPLATES)
)


@tenant_manual_orders_ui_bp.context_processor
def inject_context():
    try:
        settings = PlatformSettingsService().get_singleton()
    except Exception:
        settings = None
    locale = get_admin_locale()
    return {
        "platform_settings": settings,
        "t": t,
        "locale": locale,
        "lang": locale,
        "dir": "rtl" if locale == "ar" else "ltr",
        "tenant": getattr(g, "tenant", None),
    }


@tenant_manual_orders_ui_bp.after_request
def remember_locale(response):
    return remember_admin_locale(response)


@tenant_manual_orders_ui_bp.get("/orders")
def manual_orders_page():
    title = t("الطلبات", "Orders")
    return render_template(
        "store_orders.html", page_title=title, active_nav="manual_orders"
    )
