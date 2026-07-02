from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from workflow.workflow import WorkflowRun
from workflow_svc.workflow_service import WorkflowService

workflow_bp = Blueprint("workflow", __name__)
_svc = WorkflowService()


@workflow_bp.route("/runs", methods=["GET"])
def list_runs():
    try:
        tenant = require_tenant_context()
        runs = WorkflowRun.query.filter_by(tenant_id=tenant.id).order_by(WorkflowRun.created_at.desc()).all()
        return jsonify({"runs": [r.to_dict() for r in runs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@workflow_bp.route("/definitions", methods=["GET"])
def list_definitions():
    try:
        tenant = require_tenant_context()
        definitions = _svc.list_definitions(tenant.id)
        return jsonify({"definitions": [d.to_dict() for d in definitions]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@workflow_bp.route("/definitions", methods=["POST"])
def create_definition():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        wf = _svc.create_definition(
            tenant_id=tenant.id, name=data["name"], trigger_event=data["trigger_event"],
            actions=data["actions"], conditions=data.get("conditions"),
        )
        return jsonify({"definition": wf.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
