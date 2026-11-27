"""Platform admin HTML routes — /admin/platform/* (wave 5 #54)."""

from __future__ import annotations

from pathlib import Path

from admin_locale import get_admin_locale, remember_admin_locale, t
from flask import Blueprint, g, render_template

from platform_svc.platform_settings_service import PlatformSettingsService

_ADMIN_ROOT = Path(__file__).resolve().parents[1]

platform_admin_bp = Blueprint(
    "platform_admin",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


@platform_admin_bp.context_processor
def inject_platform_settings():
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
    }


@platform_admin_bp.after_request
def remember_locale(response):
    return remember_admin_locale(response)


@platform_admin_bp.get("/backups")
def platform_backups_page():
    return render_template(
        "platform_backups.html",
        page_title=t("نسخ المنصة", "Platform backups"),
        active_nav="backups",
    )


@platform_admin_bp.get("/dashboard")
def platform_dashboard():
    from tenant.tenant import Tenant

    stores = (
        Tenant.query.filter_by(deleted_at=None)
        .order_by(Tenant.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "platform_dashboard.html",
        page_title=t("لوحة المنصة", "Platform dashboard"),
        active_nav="dashboard",
        stores=stores,
    )


@platform_admin_bp.get("/tenants")
def platform_tenants():
    return render_template(
        "platform_tenants.html",
        page_title=t("إدارة المتاجر", "Store management"),
        active_nav="tenants",
    )


@platform_admin_bp.get("/users")
def platform_users():
    return render_template(
        "platform_users.html",
        page_title=t("إدارة المستخدمين", "User management"),
        active_nav="users",
    )


@platform_admin_bp.get("/settings")
def platform_settings():
    return render_template(
        "platform_settings.html",
        page_title=t("إعدادات المنصة", "Platform settings"),
        active_nav="settings",
    )


@platform_admin_bp.get("/reconciliation")
def reconciliation_dashboard():
    return render_template(
        "reconciliation_dashboard.html",
        page_title=t("التسوية المالية", "Financial reconciliation"),
        active_nav="reconciliation",
    )


@platform_admin_bp.get("/currency")
def platform_currency():
    return render_template(
        "currency_management.html",
        page_title=t("العملات وأسعار الصرف", "Currencies & exchange rates"),
        active_nav="currency",
    )


@platform_admin_bp.get("/audit")
def platform_audit():
    return render_template(
        "platform_audit_management.html",
        page_title=t("تدقيق المنصة", "Platform audit"),
        active_nav="audit",
    )


@platform_admin_bp.get("/stores/<int:tenant_id>/finance")
def store_financial_report(tenant_id: int):
    return render_template(
        "store_financial_report.html",
        tenant_id=tenant_id,
        page_title=t("التقرير المالي للمتجر", "Store financial report"),
        active_nav="finance",
    )
