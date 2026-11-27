"""Tenant manual (WhatsApp) order management API."""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from order.order import Order, OrderItem
from order_svc.whatsapp_order_service import WhatsAppOrderService
from orion.extensions import db

tenant_orders_bp = Blueprint("tenant_orders", __name__)
_service = WhatsAppOrderService()


@tenant_orders_bp.get("/orders")
def list_manual_orders():
    try:
        require_tenant_admin()
        _service.expire_stale()
        from tenant.tenant import Tenant

        rows = (
            Order.query.filter_by(
                tenant_id=g.tenant_id, shipping_method_code="whatsapp"
            )
            .order_by(Order.created_at.desc())
            .limit(100)
            .all()
        )
        tenant = db.session.get(Tenant, g.tenant_id)
        currency = (tenant.default_currency if tenant else None) or "ILS"
        out = []
        for order in rows:
            items = [
                item.to_dict()
                for item in OrderItem.query.filter_by(order_id=order.id).all()
            ]
            out.append({**order.to_dict(), "currency": currency, "items": items})
        return jsonify({"orders": out}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_orders_bp.post("/orders/<public_id>/confirm")
def confirm_manual_order(public_id):
    try:
        require_tenant_admin()
        order = _service.confirm(g.tenant_id, public_id)
        return jsonify({"order": order.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_orders_bp.post("/orders/<public_id>/cancel")
def cancel_manual_order(public_id):
    try:
        require_tenant_admin()
        order = _service.cancel(g.tenant_id, public_id)
        return jsonify({"order": order.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
