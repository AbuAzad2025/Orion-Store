"""OMS warehouse and fulfillment API (wave 9 #63)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from oms.fulfillment import FulfillmentItem
from oms_svc.oms_service import OmsService
from order_svc.order_service import OrderService

oms_bp = Blueprint("oms", __name__)
_oms = OmsService()
_orders = OrderService()


@oms_bp.get("/warehouses")
def list_warehouses():
    try:
        require_tenant_admin()
        rows = _oms.list_warehouses(g.tenant_id)
        return jsonify({"warehouses": [w.to_dict() for w in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@oms_bp.post("/warehouses")
def create_warehouse():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        wh = _oms.create_warehouse(
            tenant_id=g.tenant_id,
            name=data["name"],
            code=data["code"],
            is_default=bool(data.get("is_default", False)),
            address=data.get("address"),
        )
        return jsonify({"warehouse": wh.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing name or code."}), 400


@oms_bp.put("/inventory")
def upsert_inventory():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        row = _oms.upsert_inventory(
            tenant_id=g.tenant_id,
            warehouse_id=data["warehouse_id"],
            product_id=data["product_id"],
            quantity=int(data["quantity"]),
        )
        return jsonify({"inventory": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing warehouse_id, product_id, or quantity."}), 400


@oms_bp.post("/fulfillments")
def create_fulfillment():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        order = _orders.get_by_public_id(g.tenant_id, data["order_public_id"])
        row = _oms.create_fulfillment(
            tenant_id=g.tenant_id,
            order_id=order.id,
            warehouse_id=data.get("warehouse_id"),
        )
        items = FulfillmentItem.query.filter_by(fulfillment_id=row.id).all()
        return (
            jsonify(
                {
                    "fulfillment": row.to_dict(),
                    "items": [i.to_dict() for i in items],
                }
            ),
            201,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing order_public_id."}), 400


@oms_bp.post("/fulfillments/<int:fulfillment_id>/ship")
def ship_fulfillment(fulfillment_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        row = _oms.ship_fulfillment(
            tenant_id=g.tenant_id,
            fulfillment_id=fulfillment_id,
            tracking_number=data.get("tracking_number"),
        )
        return jsonify({"fulfillment": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
