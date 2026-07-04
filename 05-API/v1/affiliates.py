from flask import Blueprint, g, jsonify, request

from affiliate.affiliate import Affiliate, AffiliateCommission, AffiliateProgram
from affiliate_svc.affiliate_service import AffiliateService
from core.exceptions import OrionError
from core.middleware import require_tenant_admin

affiliates_bp = Blueprint("affiliates", __name__)
_svc = AffiliateService()


@affiliates_bp.route("/programs", methods=["GET"])
def list_programs():
    try:
        require_tenant_admin()
        programs = AffiliateProgram.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"programs": [p.to_dict() for p in programs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@affiliates_bp.route("/affiliates", methods=["GET"])
def list_affiliates():
    try:
        require_tenant_admin()
        affiliates = Affiliate.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"affiliates": [a.to_dict() for a in affiliates]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@affiliates_bp.route("/commissions", methods=["GET"])
def list_commissions():
    try:
        require_tenant_admin()
        commissions = AffiliateCommission.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"commissions": [c.to_dict() for c in commissions]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@affiliates_bp.route("/programs", methods=["POST"])
def create_program():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        program = _svc.create_program(
            tenant_id=g.tenant_id,
            name=data["name"],
            code=data["code"],
            commission_type=data["commission_type"],
            commission_value=data["commission_value"],
            cookie_days=int(data.get("cookie_days", 30)),
        )
        return jsonify({"program": program.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@affiliates_bp.route("/register", methods=["POST"])
def register_affiliate():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        affiliate = _svc.register_affiliate(
            tenant_id=g.tenant_id,
            program_id=int(data["program_id"]),
            email=data["email"],
        )
        return jsonify({"affiliate": affiliate.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@affiliates_bp.route("/commissions", methods=["POST"])
def record_commission():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        c = _svc.record_commission(
            tenant_id=g.tenant_id,
            affiliate_id=int(data["affiliate_id"]),
            order_id=int(data["order_id"]),
            amount=data["amount"],
        )
        return jsonify({"commission": c.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
