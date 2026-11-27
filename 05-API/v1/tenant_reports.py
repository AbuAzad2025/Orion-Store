"""Tenant sales & profit report API — /api/v1/tenant/reports/*."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin
from order.order import Order
from order_svc.sales_report_service import SalesReportService
from platform_models.invoice import Invoice

tenant_reports_bp = Blueprint("tenant_reports", __name__)
_service = SalesReportService()


def _date(value):
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError as exc:
        raise ValidationError("Invalid report date.") from exc


@tenant_reports_bp.get("/reports/sales")
def sales_report():
    try:
        require_tenant_admin()
        start = _date(request.args.get("from"))
        end = _date(request.args.get("to"))
        return jsonify({"report": _service.build(g.tenant_id, start, end)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_reports_bp.get("/invoices")
def tenant_invoices():
    try:
        require_tenant_admin()
        rows = (
            Invoice.query.filter_by(tenant_id=g.tenant_id)
            .order_by(Invoice.issued_at.desc())
            .limit(100)
            .all()
        )
        items = []
        for invoice in rows:
            order = Order.query.get(invoice.order_id)
            items.append(
                {
                    **invoice.to_dict(),
                    "order_number": order.order_number if order else "",
                    "order_public_id": str(order.public_id) if order else "",
                }
            )
        return jsonify({"invoices": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
