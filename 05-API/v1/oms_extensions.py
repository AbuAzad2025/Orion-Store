from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from oms_svc.extensions.inventory_transfer_service import InventoryTransferService
from oms_svc.oms_service import OmsService

oms_ext_bp = Blueprint("oms_ext", __name__)
_svc = InventoryTransferService()
_oms = OmsService()


@oms_ext_bp.route("/transfers", methods=["POST"])
def create_transfer():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        transfer = _svc.create_transfer(
            tenant_id=g.tenant_id,
            from_warehouse_id=int(data["from_warehouse_id"]),
            to_warehouse_id=int(data["to_warehouse_id"]),
            notes=data.get("notes"),
        )
        return jsonify({"transfer": transfer.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@oms_ext_bp.route("/transfers/<int:transfer_id>/items", methods=["POST"])
def add_transfer_item(transfer_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _svc.add_item(
            tenant_id=g.tenant_id,
            transfer_id=transfer_id,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@oms_ext_bp.route("/transfers/<int:transfer_id>/complete", methods=["POST"])
def complete_transfer(transfer_id: int):
    try:
        require_tenant_admin()
        transfer = _svc.complete_transfer(
            tenant_id=g.tenant_id, transfer_id=transfer_id
        )
        return jsonify({"transfer": transfer.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@oms_ext_bp.route("/warehouses", methods=["GET"])
def list_warehouses():
    try:
        require_tenant_admin()
        whs = _oms.list_warehouses(g.tenant_id)
        return jsonify({"warehouses": [w.to_dict() for w in whs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
