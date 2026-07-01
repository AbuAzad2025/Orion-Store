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


@tenant_admin_bp.get("/subscriptions")
def tenant_subscriptions():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "subscriptions_management.html",
        tenant=tenant,
        page_title="الاشتراكات",
        active_nav="subscriptions",
    )


@tenant_admin_bp.get("/tax")
def tenant_tax():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "tax_management.html",
        tenant=tenant,
        page_title="الضرائب",
        active_nav="tax",
    )


@tenant_admin_bp.get("/bopis")
def tenant_bopis():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "bopis_management.html",
        tenant=tenant,
        page_title="الاستلام من المتجر",
        active_nav="bopis",
    )


@tenant_admin_bp.get("/bundles")
def tenant_bundles():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "bundles_management.html",
        tenant=tenant,
        page_title="الحزم",
        active_nav="bundles",
    )


@tenant_admin_bp.get("/store-credit")
def tenant_store_credit():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "store_credit_management.html",
        tenant=tenant,
        page_title="رصيد المتجر",
        active_nav="store_credit",
    )


@tenant_admin_bp.get("/draft-orders")
def tenant_draft_orders():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "draft_orders_management.html",
        tenant=tenant,
        page_title="الطلبات المسودة",
        active_nav="draft_orders",
    )
