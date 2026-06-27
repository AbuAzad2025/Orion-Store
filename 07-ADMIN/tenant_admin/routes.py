"""Tenant admin HTML routes — /admin/store/* (wave 5 #52-53)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, render_template

_ADMIN_ROOT = Path(__file__).resolve().parents[1]

tenant_admin_bp = Blueprint(
    "tenant_admin",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


def _require_tenant():
    if not g.tenant:
        return None
    return g.tenant


@tenant_admin_bp.get("/dashboard")
def tenant_dashboard():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "tenant_dashboard.html",
        tenant=tenant,
        page_title="لوحة المتجر",
        active_nav="dashboard",
    )


@tenant_admin_bp.get("/gateways")
def tenant_gateways():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "tenant_gateways.html",
        tenant=tenant,
        page_title="بوابات الدفع",
        active_nav="gateways",
    )


@tenant_admin_bp.get("/documents")
def tenant_documents():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "document_templates.html",
        tenant=tenant,
        page_title="قوالب المستندات",
        active_nav="documents",
    )
