from flask import Blueprint, g, jsonify, request
from fraud_svc.fraud_service import FraudService

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

fraud_bp = Blueprint("fraud", __name__)
_svc = FraudService()


@fraud_bp.route("/rules", methods=["GET"])
def list_rules():
    try:
        require_tenant_admin()
        rules = _svc.list_rules(g.tenant_id)
        return jsonify({"rules": [r.to_dict() for r in rules]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@fraud_bp.route("/rules", methods=["POST"])
def create_rule():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        rule = _svc.create_rule(
            tenant_id=g.tenant_id,
            name=data["name"],
            rule_type=data["rule_type"],
            operator=data["operator"],
            threshold_value=data["threshold_value"],
            action=data.get("action", "review"),
        )
        return jsonify({"rule": rule.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@fraud_bp.route("/reviews", methods=["POST"])
def review_order():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        review = _svc.review_order(
            tenant_id=g.tenant_id,
            order_id=int(data["order_id"]),
            risk_score=int(data.get("risk_score", 0)),
        )
        return jsonify({"review": review.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@fraud_bp.route("/chargebacks", methods=["POST"])
def create_chargeback():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        cb = _svc.chargeback(
            tenant_id=g.tenant_id,
            payment_id=int(data["payment_id"]),
            order_id=int(data["order_id"]),
            amount=data["amount"],
            reason_code=data.get("reason_code"),
        )
        return jsonify({"chargeback": cb.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
