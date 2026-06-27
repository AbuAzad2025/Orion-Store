"""Tenant admin JSON API — /api/v1/tenant/* (wave 5)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from catalog_svc.product_service import ProductService
from core.exceptions import OrionError
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
_payments = PaymentService()

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
