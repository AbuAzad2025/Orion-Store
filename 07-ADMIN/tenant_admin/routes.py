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


@tenant_admin_bp.get("/feature-flags")
def tenant_feature_flags():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "feature_flags_management.html",
        tenant=tenant,
        page_title="ميزات المتجر",
        active_nav="feature_flags",
    )


@tenant_admin_bp.get("/returns")
def tenant_returns():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "returns_management.html",
        tenant=tenant,
        page_title="المرتجعات",
        active_nav="returns",
    )


@tenant_admin_bp.get("/b2b")
def tenant_b2b():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "b2b_management.html",
        tenant=tenant,
        page_title="B2B — الجملة",
        active_nav="b2b",
    )


@tenant_admin_bp.get("/oms")
def tenant_oms():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "oms_management.html",
        tenant=tenant,
        page_title="المستودعات والتنفيذ",
        active_nav="oms",
    )
