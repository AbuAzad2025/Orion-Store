from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from store_credit_svc.store_credit_service import StoreCreditService

store_credit_bp = Blueprint("store_credit", __name__)
_svc = StoreCreditService()


@store_credit_bp.route("/balance", methods=["GET"])
def get_balance():
    try:
        require_tenant_admin()
        email = request.args.get("customer_email", "")
        balance = _svc.get_balance(tenant_id=g.tenant_id, customer_email=email)
        return jsonify({"customer_email": email, "balance": str(balance)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@store_credit_bp.route("/add", methods=["POST"])
def add_funds():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        credit = _svc.add_funds(
            tenant_id=g.tenant_id, customer_email=data["customer_email"],
            amount=data["amount"], reason=data.get("reason"),
        )
        return jsonify({"credit": credit.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@store_credit_bp.route("/deduct", methods=["POST"])
def deduct_funds():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        credit = _svc.deduct(
            tenant_id=g.tenant_id, customer_email=data["customer_email"],
            amount=data["amount"], reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
        )
        return jsonify({"credit": credit.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@store_credit_bp.route("/transactions", methods=["GET"])
def list_transactions():
    try:
        require_tenant_admin()
        credit_id = int(request.args.get("credit_id", "0"))
        txns = _svc.list_transactions(tenant_id=g.tenant_id, credit_id=credit_id)
        return jsonify({"transactions": [t.to_dict() for t in txns]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
