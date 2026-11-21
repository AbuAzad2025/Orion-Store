from draft_order_svc.draft_order_service import DraftOrderService
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

draft_orders_bp = Blueprint("draft_orders", __name__)
_svc = DraftOrderService()


@draft_orders_bp.route("", methods=["GET"])
def list_drafts():
    try:
        require_tenant_admin()
        drafts = _svc.list_drafts(g.tenant_id)
        return jsonify({"draft_orders": [d.to_dict() for d in drafts]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@draft_orders_bp.route("", methods=["POST"])
def create_draft():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        draft = _svc.create_draft(
            tenant_id=g.tenant_id,
            customer_email=data.get("customer_email"),
            notes=data.get("notes"),
            shipping_address=data.get("shipping_address"),
            send_email_invite=data.get("send_email_invite", False),
        )
        return jsonify({"draft_order": draft.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@draft_orders_bp.route("/<int:draft_id>/items", methods=["POST"])
def add_item(draft_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _svc.add_item(
            tenant_id=g.tenant_id,
            draft_id=draft_id,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@draft_orders_bp.route("/<int:draft_id>/convert", methods=["POST"])
def convert(draft_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        order = _svc.convert_to_order(
            tenant_id=g.tenant_id,
            draft_id=draft_id,
            customer_email=data.get("customer_email"),
        )
        return jsonify({"order": order.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
