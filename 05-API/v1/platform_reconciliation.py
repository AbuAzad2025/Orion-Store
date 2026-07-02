"""Platform reconciliation API (§0.15 gap closure)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from core.exceptions import OrionError
from core.middleware import require_platform_admin
from orion.extensions import db
from platform_svc.reconciliation_service import ReconciliationService
from tenant.tenant import Tenant
from user.user import User

_reconciliation = ReconciliationService()


def register_platform_reconciliation_routes(bp: Blueprint) -> None:
    @bp.get("/stats")
    def platform_stats():
        try:
            require_platform_admin()
            tenant_count = Tenant.query.filter(Tenant.deleted_at.is_(None)).count()
            user_count = User.query.filter(User.deleted_at.is_(None)).count()
            active_tenant_count = Tenant.query.filter(
                Tenant.deleted_at.is_(None), Tenant.is_active.is_(True)
            ).count()
            active_user_count = User.query.filter(
                User.deleted_at.is_(None), User.is_active.is_(True)
            ).count()
            return jsonify({
                "stats": {
                    "tenants": tenant_count,
                    "users": user_count,
                    "active_tenants": active_tenant_count,
                    "active_users": active_user_count,
                }
            }), 200
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code

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
