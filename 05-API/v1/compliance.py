from compliance.compliance import (
    ConsentRecord,
    CookieConsentSetting,
    DataSubjectRequest,
)
from compliance_svc.compliance_service import ComplianceService
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context

compliance_bp = Blueprint("compliance", __name__)
_svc = ComplianceService()


@compliance_bp.route("/consent", methods=["GET"])
def list_consent():
    try:
        require_tenant_admin()
        records = ConsentRecord.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"consent_records": [r.to_dict() for r in records]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/consent/public", methods=["POST"])
def record_visitor_consent():
    """Store a storefront visitor's cookie choice (no auth required)."""
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        choice = str(data.get("choice", "")).strip().lower()
        if choice not in ("all", "necessary"):
            return jsonify({"error": "Invalid choice."}), 400
        rec = _svc.record_consent(
            tenant_id=tenant.id,
            customer_email=data.get("email") or "anonymous",
            consent_type="cookie_banner",
            granted=choice == "all",
            ip_address=request.remote_addr,
        )
        return jsonify({"consent": rec.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/data-requests", methods=["GET"])
def list_data_requests():
    try:
        require_tenant_admin()
        requests = DataSubjectRequest.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"data_requests": [r.to_dict() for r in requests]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/cookie-settings", methods=["GET"])
def get_cookie_settings():
    try:
        require_tenant_admin()
        setting = CookieConsentSetting.query.filter_by(tenant_id=g.tenant_id).first()
        return jsonify({"cookie_settings": setting.to_dict() if setting else None}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/consent", methods=["POST"])
def record_consent():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        rec = _svc.record_consent(
            tenant_id=g.tenant_id,
            customer_email=data["customer_email"],
            consent_type=data["consent_type"],
            granted=data.get("granted", True),
            ip_address=data.get("ip_address"),
        )
        return jsonify({"consent": rec.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@compliance_bp.route("/data-requests", methods=["POST"])
def create_data_request():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        req = _svc.create_data_request(
            tenant_id=g.tenant_id,
            customer_email=data["customer_email"],
            request_type=data["request_type"],
        )
        return jsonify({"request": req.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@compliance_bp.route("/cookie-settings", methods=["PUT"])
def upsert_cookie_settings():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        settings = _svc.upsert_cookie_settings(
            tenant_id=g.tenant_id,
            banner_message=data.get("banner_message"),
            is_active=data.get("is_active", True),
        )
        return jsonify({"settings": settings.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@compliance_bp.route("/sso", methods=["GET"])
def list_sso():
    try:
        require_tenant_admin()
        providers = _svc.list_sso(g.tenant_id)
        return jsonify({"sso_providers": [p.to_dict() for p in providers]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/sso", methods=["POST"])
def create_sso():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        provider = _svc.create_sso(
            tenant_id=g.tenant_id,
            provider_type=data["provider_type"],
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            issuer_url=data.get("issuer_url"),
        )
        return jsonify({"sso_provider": provider.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@compliance_bp.route("/data-requests/<int:request_id>/export", methods=["POST"])
def export_data_request(request_id: int):
    try:
        require_tenant_admin()
        payload = _svc.export_subject_data(tenant_id=g.tenant_id, request_id=request_id)
        return jsonify(payload), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@compliance_bp.route("/data-requests/<int:request_id>/execute-delete", methods=["POST"])
def execute_delete_data_request(request_id: int):
    try:
        require_tenant_admin()
        result = _svc.execute_subject_deletion(
            tenant_id=g.tenant_id, request_id=request_id
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
