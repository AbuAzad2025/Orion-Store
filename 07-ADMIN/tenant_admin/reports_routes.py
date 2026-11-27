"""Tenant report HTML routes (kept separate to respect file-length limits)."""

from __future__ import annotations

from pathlib import Path

from admin_locale import get_admin_locale, remember_admin_locale, t
from flask import Blueprint, g, render_template

from platform_svc.platform_settings_service import PlatformSettingsService

_TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
tenant_reports_ui_bp = Blueprint(
    "tenant_reports_ui", __name__, template_folder=str(_TEMPLATES)
)


@tenant_reports_ui_bp.context_processor
def inject_report_context():
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


@tenant_reports_ui_bp.after_request
def remember_locale(response):
    return remember_admin_locale(response)


@tenant_reports_ui_bp.get("/backups")
def tenant_backups_page():
    title = t("النسخ الاحتياطي", "Backups")
    return render_template("backups.html", page_title=title, active_nav="backups")


@tenant_reports_ui_bp.get("/invoices")
def tenant_invoices_page():
    title = t("الفواتير", "Invoices")
    return render_template("invoices.html", page_title=title, active_nav="invoices")


@tenant_reports_ui_bp.get("/reports/sales")
def tenant_sales_report():
    title = t("المبيعات والأرباح", "Sales & profit")
    return render_template(
        "sales_report.html", page_title=title, active_nav="sales_report"
    )
