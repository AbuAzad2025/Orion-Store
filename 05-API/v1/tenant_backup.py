"""Tenant backup create/list/download API — admin UI only, no restore."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, send_file

from backup_svc.backup_service import BackupError, BackupService
from core.middleware import require_tenant_admin
from orion.extensions import db
from tenant.tenant import Tenant

tenant_backup_bp = Blueprint("tenant_backup", __name__)
_service = BackupService()


def _slug() -> str:
    tenant = db.session.get(Tenant, g.tenant_id)
    return tenant.slug if tenant else ""


@tenant_backup_bp.get("/backups")
def list_backups():
    try:
        require_tenant_admin()
        return jsonify({"backups": _service.list_store(_slug())}), 200
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 400


@tenant_backup_bp.post("/backups")
def create_backup():
    try:
        require_tenant_admin()
        return jsonify({"backup": _service.create_store(_slug())}), 201
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 500


@tenant_backup_bp.get("/backups/<name>/download")
def download_backup(name: str):
    try:
        require_tenant_admin()
        path = _service.store_path(_slug(), name)
        return send_file(path, as_attachment=True, download_name=name)
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 404
