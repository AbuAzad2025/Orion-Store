"""Platform backup create/list/download API — admin UI only, no restore."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file

from backup_svc.backup_service import BackupError, BackupService
from core.middleware import require_platform_admin

platform_backup_bp = Blueprint("platform_backup", __name__)
_service = BackupService()


@platform_backup_bp.get("/backups")
def list_backups():
    try:
        require_platform_admin()
        return jsonify({"backups": _service.list_platform()}), 200
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 400


@platform_backup_bp.post("/backups")
def create_backup():
    try:
        require_platform_admin()
        return jsonify({"backup": _service.create_platform()}), 201
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 500


@platform_backup_bp.get("/backups/<name>/download")
def download_backup(name: str):
    try:
        require_platform_admin()
        kind = request.args.get("kind", "dump")
        backup = next(
            (
                b
                for b in _service.list_platform()
                if b["dump"] == name or b["assets"] == name
            ),
            None,
        )
        if backup is None:
            raise BackupError("Backup not found.")
        path = _service.platform_path(name)
        download_name = name if kind != "assets" else (backup["assets"] or name)
        return send_file(path, as_attachment=True, download_name=download_name)
    except BackupError as exc:
        return jsonify({"error": str(exc)}), 404
