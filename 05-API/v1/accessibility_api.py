from accessibility_svc.accessibility_service import AccessibilityService
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

accessibility_bp = Blueprint("accessibility", __name__)
_svc = AccessibilityService()


@accessibility_bp.route("/audits", methods=["GET"])
def list_audits():
    try:
        require_tenant_admin()
        audits = _svc.list_audits(g.tenant_id)
        return jsonify({"audits": [a.to_dict() for a in audits]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@accessibility_bp.route("/audits", methods=["POST"])
def record_audit():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        audit = _svc.record_audit(
            tenant_id=g.tenant_id,
            page_url=data["page_url"],
            score=int(data["score"]),
            issues=data.get("issues"),
        )
        return jsonify({"audit": audit.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
