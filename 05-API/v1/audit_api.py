from flask import Blueprint, g, jsonify, request

from audit_svc.audit_v2_service import AuditV2Service
from core.exceptions import OrionError
from core.middleware import require_platform_admin

audit_bp = Blueprint("audit", __name__)
_svc = AuditV2Service()


@audit_bp.route("/reports", methods=["GET"])
def list_reports():
    try:
        require_platform_admin()
        reports = _svc.list_reports()
        return jsonify({"reports": [r.to_dict() for r in reports]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@audit_bp.route("/reports", methods=["POST"])
def create_report():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        report = _svc.create_report(
            report_type=data["report_type"],
            generated_by=int(data["generated_by"]),
            summary=data.get("summary", {}),
            details=data.get("details"),
        )
        return jsonify({"report": report.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@audit_bp.route("/logs", methods=["GET"])
def list_logs():
    try:
        require_platform_admin()
        logs = _svc.list_logs(limit=int(request.args.get("limit", 50)))
        return jsonify({"logs": [l.to_dict() for l in logs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@audit_bp.route("/logs", methods=["POST"])
def log_action():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        log = _svc.log_action(
            user_id=int(data["user_id"]),
            action=data["action"],
            target_type=data.get("target_type"),
            target_id=data.get("target_id"),
            details=data.get("details"),
        )
        return jsonify({"log": log.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
