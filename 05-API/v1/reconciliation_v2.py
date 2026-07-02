from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from reconciliation_svc.reconciliation_v2_service import ReconciliationV2Service

reconciliation_v2_bp = Blueprint("reconciliation_v2", __name__)
_svc = ReconciliationV2Service()


@reconciliation_v2_bp.route("/runs", methods=["GET"])
def list_runs():
    try:
        require_tenant_admin()
        runs = _svc.list_runs(g.tenant_id)
        return jsonify({"runs": [r.to_dict() for r in runs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@reconciliation_v2_bp.route("/runs", methods=["POST"])
def create_run():
    try:
        require_tenant_admin()
        run = _svc.create_run(tenant_id=g.tenant_id)
        return jsonify({"run": run.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@reconciliation_v2_bp.route("/runs/<int:run_id>/items", methods=["POST"])
def add_item(run_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _svc.add_item(
            tenant_id=g.tenant_id, run_id=run_id, financial_event_id=int(data["financial_event_id"]),
            expected_amount=data["expected_amount"], actual_amount=data["actual_amount"],
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@reconciliation_v2_bp.route("/runs/<int:run_id>/complete", methods=["POST"])
def complete_run(run_id: int):
    try:
        require_tenant_admin()
        run = _svc.complete_run(run_id=run_id, tenant_id=g.tenant_id)
        return jsonify({"run": run.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
