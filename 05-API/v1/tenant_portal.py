"""Tenant admin JSON API — /api/v1/tenant/* (wave 5)."""

from __future__ import annotations

from feature_flag_svc.feature_flag_service import FeatureFlagService
from flask import Blueprint, g, jsonify, request
from i18n_svc.translation_service import TranslationService

from bnpl_svc.bnpl_service import BnplService
from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError, OrionError
from core.middleware import require_tenant_admin
from core.pagination import paginate_query, paginated_payload, pagination_params
from order_svc.order_service import OrderService
from payment_svc.payment_service import PaymentService
from platform_models.tenant_gateway import TenantPaymentGateway
from platform_svc.document_template_service import DocumentTemplateService
from tenant_gateway_svc.gateway_service import GatewayService

tenant_portal_bp = Blueprint("tenant_portal", __name__)
_gateways = GatewayService()
_templates = DocumentTemplateService()
_orders = OrderService()
_products = ProductService()
_categories = CategoryService()
_translations = TranslationService()
_flags = FeatureFlagService()
_payments = PaymentService()
_bnpl = BnplService()

_VALID_TEMPLATE = (
    "<div>{{order_number}}</div>"
    '<footer id="azadexa-platform-footer" data-immutable="true"></footer>'
)


def _template_dict(row) -> dict:
    return {
        "id": row.id,
        "document_type": row.document_type,
        "locale": row.locale,
        "body_html": row.body_html,
        "is_active": row.is_active,
    }


@tenant_portal_bp.get("/dashboard")
def tenant_dashboard_api():
    try:
        require_tenant_admin()
        orders = _orders.list_for_tenant(g.tenant_id)
        products = _products.list_for_tenant(g.tenant_id)
        paid = sum(1 for o in orders if o.payment_status == "paid")
        return (
            jsonify(
                {
                    "tenant": g.tenant.to_dict(),
                    "stats": {
                        "orders_total": len(orders),
                        "orders_paid": paid,
                        "products_total": len(products),
                        "products_published": sum(
                            1 for p in products if p.is_published
                        ),
                    },
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.get("/gateways")
def list_gateways():
    try:
        require_tenant_admin()
        page, per_page = pagination_params()
        items, meta = paginate_query(
            TenantPaymentGateway.query.filter_by(tenant_id=g.tenant_id),
            page,
            per_page,
        )
        return (
            jsonify(
                paginated_payload("gateways", items, meta, lambda gw: gw.to_dict())
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.post("/gateways/cod")
def ensure_cod_gateway():
    try:
        require_tenant_admin()
        gateway = _gateways.ensure_cod_gateway(g.tenant_id)
        return jsonify({"gateway": gateway.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.post("/gateways/paypal")
def connect_paypal_gateway():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        gateway = _gateways.upsert_paypal(
            tenant_id=g.tenant_id,
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            webhook_secret=data.get("webhook_secret"),
            is_sandbox=bool(data.get("is_sandbox", True)),
            is_enabled=bool(data.get("is_enabled", True)),
        )
        return jsonify({"gateway": gateway.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.get("/bnpl/providers")
def list_bnpl_providers():
    try:
        require_tenant_admin()
        providers = _bnpl.list_providers(g.tenant_id)
        return jsonify({"providers": [row.to_dict() for row in providers]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.put("/bnpl/providers/<provider>")
def upsert_bnpl_provider(provider: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        row = _bnpl.upsert_provider(
            tenant_id=g.tenant_id,
            provider=provider,
            merchant_id=data.get("merchant_id"),
            api_key=data.get("api_key"),
            is_enabled=bool(data.get("is_enabled", True)),
            is_sandbox=bool(data.get("is_sandbox", True)),
            config=data.get("config"),
        )
        return jsonify({"provider": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.get("/document-templates")
def list_document_templates():
    try:
        require_tenant_admin()
        page, per_page = pagination_params()
        from platform_models.invoice import TenantDocumentTemplate

        items, meta = paginate_query(
            TenantDocumentTemplate.query.filter_by(tenant_id=g.tenant_id).order_by(
                TenantDocumentTemplate.document_type
            ),
            page,
            per_page,
        )
        return (
            jsonify(
                paginated_payload("templates", items, meta, lambda r: _template_dict(r))
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.put("/document-templates/<document_type>")
def upsert_document_template(document_type: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        body_html = data.get("body_html") or _VALID_TEMPLATE
        row = _templates.upsert(
            tenant_id=g.tenant_id,
            document_type=document_type,
            locale=data.get("locale", "ar"),
            body_html=body_html,
            is_active=bool(data.get("is_active", True)),
        )
        return jsonify({"template": _template_dict(row)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.post("/payments/<payment_public_id>/refund")
def refund_payment(payment_public_id: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        result = _payments.refund(
            tenant_id=g.tenant_id,
            payment_public_id=payment_public_id,
            reason=data.get("reason"),
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.get("/feature-flags")
def list_feature_flags():
    try:
        require_tenant_admin()
        return jsonify({"flags": _flags.list_for_tenant(g.tenant_id)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.put("/feature-flags/<code>")
def set_feature_flag(code: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        result = _flags.set_tenant_override(
            tenant_id=g.tenant_id,
            code=code,
            value=bool(data.get("value", False)),
            reason=data.get("reason"),
            set_by=g.user.id if g.user else None,
        )
        return jsonify({"flag": result}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.get("/products/<public_id>/translations")
def list_product_translations(public_id: str):
    try:
        require_tenant_admin()
        product = _products.get_by_public_id(g.tenant_id, public_id)
        rows = _translations.list_product_translations(g.tenant_id, product.id)
        return (
            jsonify(
                {
                    "product_id": product.id,
                    "translations": [r.to_dict() for r in rows],
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_portal_bp.put("/products/<public_id>/translations/<locale>")
def upsert_product_translation(public_id: str, locale: str):
    try:
        require_tenant_admin()
        product = _products.get_by_public_id(g.tenant_id, public_id)
        data = request.get_json(silent=True) or {}
        row = _translations.upsert_product_translation(
            tenant_id=g.tenant_id,
            product=product,
            locale=locale,
            name=data["name"],
            description=data.get("description"),
            meta_title=data.get("meta_title"),
            meta_description=data.get("meta_description"),
        )
        return jsonify({"translation": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing name."}), 400


@tenant_portal_bp.put("/categories/<int:category_id>/translations/<locale>")
def upsert_category_translation(category_id: int, locale: str):
    try:
        require_tenant_admin()
        category = (
            _categories.query_for_tenant(g.tenant_id).filter_by(id=category_id).first()
        )
        if not category:
            raise NotFoundError("Category not found.")
        data = request.get_json(silent=True) or {}
        row = _translations.upsert_category_translation(
            tenant_id=g.tenant_id,
            category=category,
            locale=locale,
            name=data["name"],
            description=data.get("description"),
            slug=data.get("slug"),
        )
        return jsonify({"translation": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing name."}), 400
