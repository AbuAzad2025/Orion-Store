"""Platform admin HTML routes — /admin/platform/* (wave 5 #54)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, render_template

from core.jwt_auth import issue_tokens_for_user
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
    return {"platform_settings": settings}


@platform_admin_bp.context_processor
def inject_admin_token():
    if g.user and g.is_platform_admin:
        return {"admin_token": issue_tokens_for_user(g.user)["access_token"]}
    return {}


@platform_admin_bp.get("/dashboard")
def platform_dashboard():
    return render_template(
        "platform_dashboard.html",
        page_title="لوحة المنصة",
        active_nav="dashboard",
    )


@platform_admin_bp.get("/tenants")
def platform_tenants():
    return render_template(
        "platform_tenants.html",
        page_title="إدارة المتاجر",
        active_nav="tenants",
    )


@platform_admin_bp.get("/users")
def platform_users():
    return render_template(
        "platform_users.html",
        page_title="إدارة المستخدمين",
        active_nav="users",
    )


@platform_admin_bp.get("/settings")
def platform_settings():
    return render_template(
        "platform_settings.html",
        page_title="إعدادات المنصة",
        active_nav="settings",
    )


@platform_admin_bp.get("/reconciliation")
def reconciliation_dashboard():
    return render_template(
        "reconciliation_dashboard.html",
        page_title="التسوية المالية",
        active_nav="reconciliation",
    )


@platform_admin_bp.get("/stores/<int:tenant_id>/finance")
def store_financial_report(tenant_id: int):
    return render_template(
        "store_financial_report.html",
        tenant_id=tenant_id,
        page_title="التقرير المالي للمتجر",
        active_nav="finance",
    )
