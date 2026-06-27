"""Platform admin HTML routes — /admin/platform/* (wave 5 #54)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, render_template

_ADMIN_ROOT = Path(__file__).resolve().parents[1]

platform_admin_bp = Blueprint(
    "platform_admin",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


@platform_admin_bp.get("/dashboard")
def platform_dashboard():
    return render_template(
        "platform_dashboard.html",
        page_title="لوحة المنصة",
        active_nav="dashboard",
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
