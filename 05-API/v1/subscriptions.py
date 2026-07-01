from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from subscription_svc.subscription_service import SubscriptionService

subscriptions_bp = Blueprint("subscriptions", __name__)
_svc = SubscriptionService()


@subscriptions_bp.route("/plans", methods=["GET"])
def list_plans():
    try:
        tenant = require_tenant_context()
        return jsonify({"plans": [p.to_dict() for p in _svc.list_plans(tenant.id)]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@subscriptions_bp.route("/plans", methods=["POST"])
def create_plan():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        plan = _svc.create_plan(
            tenant_id=tenant.id, name=data["name"], code=data["code"],
            billing_period_days=int(data["billing_period_days"]),
            price=data["price"], trial_period_days=int(data.get("trial_period_days", 0)),
            currency=data.get("currency", "ILS"),
            max_orders_per_cycle=data.get("max_orders_per_cycle"),
            max_products=data.get("max_products"),
        )
        return jsonify({"plan": plan.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@subscriptions_bp.route("/subscribe", methods=["POST"])
def subscribe():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        sub = _svc.subscribe(
            tenant_id=tenant.id, plan_id=int(data["plan_id"]),
            customer_email=data["customer_email"],
        )
        return jsonify({"subscription": sub.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@subscriptions_bp.route("/subscriptions", methods=["GET"])
def list_subscriptions():
    try:
        tenant = require_tenant_context()
        return jsonify({"subscriptions": [s.to_dict() for s in _svc.list_subscriptions(tenant.id)]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@subscriptions_bp.route("/subscriptions/<int:sub_id>/cancel", methods=["POST"])
def cancel_subscription(sub_id: int):
    try:
        tenant = require_tenant_context()
        sub = _svc.cancel(tenant_id=tenant.id, subscription_id=sub_id)
        return jsonify({"subscription": sub.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@subscriptions_bp.route("/digital-assets", methods=["POST"])
def create_asset():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        asset = _svc.create_digital_asset(
            tenant_id=tenant.id, product_id=int(data["product_id"]),
            file_url=data["file_url"], file_name=data["file_name"],
            mime_type=data.get("mime_type", "application/octet-stream"),
            max_downloads=int(data.get("max_downloads", 5)),
        )
        return jsonify({"asset": asset.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@subscriptions_bp.route("/digital-assets/<int:asset_id>/download", methods=["POST"])
def create_download(asset_id: int):
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        download = _svc.create_download(
            tenant_id=tenant.id, asset_id=asset_id, order_id=int(data["order_id"]),
        )
        return jsonify({"download": download.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@subscriptions_bp.route("/licenses", methods=["POST"])
def generate_license():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        lic = _svc.generate_license(
            tenant_id=tenant.id, order_item_id=int(data["order_item_id"]),
            product_id=int(data["product_id"]),
        )
        return jsonify({"license": lic.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
