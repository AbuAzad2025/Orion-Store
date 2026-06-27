"""Platform store financial APIs (wave 5 #54)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from core.exceptions import OrionError
from core.middleware import require_platform_admin
from platform_svc.store_financial_service import StoreFinancialReportService

_report = StoreFinancialReportService()


def register_platform_store_routes(bp: Blueprint) -> None:
    @bp.get("/stores/<int:tenant_id>/financial-report")
    def store_financial_report(tenant_id: int):
        try:
            require_platform_admin()
            report = _report.build(tenant_id)
            return jsonify(report), 200
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
