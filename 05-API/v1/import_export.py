from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from import_export_svc.import_export_service import ImportExportService

import_export_bp = Blueprint("import_export", __name__)
_svc = ImportExportService()


@import_export_bp.route("/jobs", methods=["GET"])
def list_jobs():
    try:
        require_tenant_admin()
        jobs = _svc.list_jobs(g.tenant_id)
        return jsonify({"jobs": [j.to_dict() for j in jobs]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@import_export_bp.route("/jobs", methods=["POST"])
def create_job():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        job = _svc.create_job(
            tenant_id=g.tenant_id,
            job_type=data["job_type"],
            entity_type=data["entity_type"],
            file_url=data.get("file_url"),
        )
        return jsonify({"job": job.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@import_export_bp.route("/jobs/<int:job_id>/progress", methods=["PUT"])
def update_progress(job_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        job = _svc.update_progress(
            job_id=job_id,
            tenant_id=g.tenant_id,
            processed=int(data.get("processed", 0)),
            failed=int(data.get("failed", 0)),
            total=int(data.get("total", 0)),
        )
        return jsonify({"job": job.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
