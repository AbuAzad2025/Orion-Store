from flask import Blueprint, jsonify, request
from stock_notification_svc.stock_notification_service import StockNotificationService

from core.exceptions import OrionError
from core.middleware import require_tenant_context

stock_notifications_bp = Blueprint("stock_notifications", __name__)
_svc = StockNotificationService()


@stock_notifications_bp.route("", methods=["POST"])
def subscribe():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        n = _svc.subscribe(
            tenant_id=tenant.id,
            product_id=int(data["product_id"]),
            customer_email=data["customer_email"],
        )
        return jsonify({"notification": n.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
