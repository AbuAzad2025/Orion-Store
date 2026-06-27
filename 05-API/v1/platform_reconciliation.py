"""Platform reconciliation API (§0.15 gap closure)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from core.exceptions import OrionError
from core.middleware import require_platform_admin
from platform_svc.reconciliation_service import ReconciliationService

_reconciliation = ReconciliationService()


def register_platform_reconciliation_routes(bp: Blueprint) -> None:
    @bp.get("/reconciliation")
    def reconciliation_status():
        try:
            require_platform_admin()
            return jsonify(_reconciliation.get_status()), 200
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code

    @bp.post("/reconciliation/run")
    def reconciliation_run():
        try:
            require_platform_admin()
            result = _reconciliation.run()
            return jsonify(result), 200
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
