"""Tenant admin HTML routes — /admin/store/* (wave 5 #52-53)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, render_template

from platform_svc.platform_settings_service import PlatformSettingsService

_ADMIN_ROOT = Path(__file__).resolve().parents[1]

tenant_admin_bp = Blueprint(
    "tenant_admin",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


@tenant_admin_bp.context_processor
def inject_platform_settings():
    try:
        settings = PlatformSettingsService().get_singleton()
    except Exception:
        settings = None
    return {"platform_settings": settings}


def _require_tenant():
    if not g.tenant:
        return None
    return g.tenant


@tenant_admin_bp.get("/dashboard")
def tenant_dashboard():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    from order.order import Order

    orders = (
        Order.query.filter_by(tenant_id=tenant.id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "tenant_dashboard.html",
        tenant=tenant,
        page_title="لوحة المتجر",
        active_nav="dashboard",
        recent_orders=orders,
    )


@tenant_admin_bp.get("/products")
def tenant_products():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "products_management.html",
        tenant=tenant,
        page_title="المنتجات",
        active_nav="products",
    )


@tenant_admin_bp.get("/pages")
def tenant_pages():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "pages_management.html",
        tenant=tenant,
        page_title="الصفحات",
        active_nav="pages",
    )


@tenant_admin_bp.get("/ui-kit")
def tenant_ui_kit():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "ui_kit.html",
        tenant=tenant,
        page_title="معاينة المكوّنات",
        active_nav="ui_kit",
    )


@tenant_admin_bp.get("/contact")
def tenant_contact():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "contact_settings.html",
        tenant=tenant,
        page_title="رقم التواصل (واتساب)",
        active_nav="contact",
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


@tenant_admin_bp.get("/vouchers")
def tenant_vouchers():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "vouchers_management.html",
        tenant=tenant,
        page_title="قسائم الخصم",
        active_nav="vouchers",
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


@tenant_admin_bp.get("/metafields")
def tenant_metafields():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "metafields_management.html",
        tenant=tenant,
        page_title="البيانات الوصفية",
        active_nav="metafields",
    )


@tenant_admin_bp.get("/currency")
def tenant_currency():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "currency_management.html",
        tenant=tenant,
        page_title="العملات",
        active_nav="currency",
    )


@tenant_admin_bp.get("/import-export")
def tenant_import_export():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "import_export_management.html",
        tenant=tenant,
        page_title="استيراد وتصدير",
        active_nav="import_export",
    )


@tenant_admin_bp.get("/app-platform")
def tenant_app_platform():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "app_platform_management.html",
        tenant=tenant,
        page_title="منصة التطبيقات",
        active_nav="app_platform",
    )


@tenant_admin_bp.get("/fraud")
def tenant_fraud():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "fraud_management.html",
        tenant=tenant,
        page_title="الاحتيال",
        active_nav="fraud",
    )


@tenant_admin_bp.get("/compliance")
def tenant_compliance():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "compliance_management.html",
        tenant=tenant,
        page_title="الامتثال",
        active_nav="compliance",
    )


@tenant_admin_bp.get("/workflows")
def tenant_workflows():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "workflows_management.html",
        tenant=tenant,
        page_title="سير العمل",
        active_nav="workflows",
    )


@tenant_admin_bp.get("/search")
def tenant_search():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "search_management.html", tenant=tenant, page_title="البحث", active_nav="search"
    )


@tenant_admin_bp.get("/affiliates")
def tenant_affiliates():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "affiliates_management.html",
        tenant=tenant,
        page_title="المسوقين",
        active_nav="affiliates",
    )


@tenant_admin_bp.get("/gift-registries")
def tenant_gift_registries():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "gift_registry_management.html",
        tenant=tenant,
        page_title="قوائم الهدايا",
        active_nav="gift_registries",
    )


@tenant_admin_bp.get("/dropship")
def tenant_dropship():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "dropship_management.html",
        tenant=tenant,
        page_title="الدروبشيبنج",
        active_nav="dropship",
    )


@tenant_admin_bp.get("/schema-markup")
def tenant_schema_markup():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "schema_markup_management.html",
        tenant=tenant,
        page_title="ترميز البيانات المنظّمة",
        active_nav="schema_markup",
    )


@tenant_admin_bp.get("/accessibility")
def tenant_accessibility():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "accessibility_management.html",
        tenant=tenant,
        page_title="إمكانية الوصول",
        active_nav="accessibility",
    )


@tenant_admin_bp.get("/live-chat")
def tenant_live_chat():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "live_chat_management.html",
        tenant=tenant,
        page_title="الدردشة المباشرة",
        active_nav="live_chat",
    )


@tenant_admin_bp.get("/reconciliation")
def tenant_reconciliation():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "reconciliation_management.html",
        tenant=tenant,
        page_title="التسوية المالية",
        active_nav="reconciliation",
    )


@tenant_admin_bp.get("/platform-audit")
def tenant_platform_audit():
    tenant = _require_tenant()
    if not tenant:
        return "Tenant context required (X-Tenant-ID).", 404
    return render_template(
        "platform_audit_management.html",
        tenant=tenant,
        page_title="تدقيق المنصة",
        active_nav="platform_audit",
    )
