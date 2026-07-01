from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from tax_svc.tax_service import TaxService

tax_bp = Blueprint("tax", __name__)
_svc = TaxService()


@tax_bp.route("/jurisdictions", methods=["GET"])
def list_jurisdictions():
    try:
        tenant = require_tenant_context()
        return jsonify({"jurisdictions": [j.to_dict() for j in _svc.list_jurisdictions(tenant.id)]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tax_bp.route("/jurisdictions", methods=["POST"])
def create_jurisdiction():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        j = _svc.create_jurisdiction(
            tenant_id=tenant.id, code=data["code"], name=data["name"],
            country_code=data["country_code"], region=data.get("region"),
        )
        return jsonify({"jurisdiction": j.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@tax_bp.route("/jurisdictions/<int:jurisdiction_id>/rates", methods=["POST"])
def set_rate(jurisdiction_id: int):
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        rate = _svc.set_rate(
            tenant_id=tenant.id, jurisdiction_id=jurisdiction_id,
            rate=data["rate"], product_tax_code=data.get("product_tax_code"),
            priority=int(data.get("priority", 0)),
        )
        return jsonify({"rate": rate.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
