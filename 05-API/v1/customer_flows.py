"""Customer self-service flows (subscriptions, credit, RFQ, gift registries)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required

from core.exceptions import AuthenticationError, OrionError
from core.middleware import require_tenant_context
from core.rate_limit import limiter

customer_flows_bp = Blueprint("customer_flows", __name__)


def _ctx():
    tenant = require_tenant_context()
    user = getattr(g, "user", None)
    if user is None:
        raise AuthenticationError("Authentication required.")
    return tenant, user


@customer_flows_bp.get("/plans")
@jwt_required()
def list_plans():
    try:
        tenant, _ = _ctx()
        from subscription_svc.subscription_service import SubscriptionService

        plans = SubscriptionService().list_plans(tenant.id)
        return jsonify({"plans": [p.to_dict() for p in plans]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@customer_flows_bp.post("/subscribe")
@jwt_required()
@limiter.limit("10 per minute")
def subscribe_to_plan():
    try:
        tenant, user = _ctx()
        data = request.get_json(silent=True) or {}
        from subscription_svc.subscription_service import SubscriptionService

        sub = SubscriptionService().subscribe(
            tenant_id=tenant.id,
            plan_id=int(data["plan_id"]),
            customer_email=user.email,
            user_id=user.id,
        )
        return jsonify({"subscription": sub.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@customer_flows_bp.get("/credit")
@jwt_required()
def my_credit():
    try:
        tenant, user = _ctx()
        from store_credit_svc.store_credit_service import StoreCreditService

        svc = StoreCreditService()
        credit = svc.get_or_create(
            tenant_id=tenant.id, customer_email=user.email, commit=False
        )
        txns = svc.list_transactions(tenant_id=tenant.id, credit_id=credit.id)
        return (
            jsonify(
                {
                    "credit": credit.to_dict(),
                    "transactions": [t.to_dict() for t in txns],
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@customer_flows_bp.get("/quote-requests")
@jwt_required()
def my_quote_requests():
    try:
        tenant, user = _ctx()
        from b2b.quote import Quote

        rows = Quote.query.filter_by(tenant_id=tenant.id, user_id=user.id).all()
        return jsonify({"quotes": [q.to_dict() for q in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@customer_flows_bp.post("/quote-requests")
@jwt_required()
@limiter.limit("10 per minute")
def create_quote_request():
    try:
        tenant, user = _ctx()
        data = request.get_json(silent=True) or {}
        from b2b_svc.b2b_service import B2BService

        svc = B2BService()
        quote = svc.create_quote(
            tenant_id=tenant.id,
            user_id=user.id,
            notes=data.get("notes"),
        )
        if data.get("product_id"):
            svc.add_quote_item(
                tenant_id=tenant.id,
                quote_id=quote.id,
                product_id=int(data["product_id"]),
                quantity=int(data.get("quantity", 1)),
            )
        return jsonify({"quote": quote.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@customer_flows_bp.get("/gift-registries")
@jwt_required()
def my_gift_registries():
    try:
        tenant, user = _ctx()
        from gift.gift_registry import GiftRegistry

        rows = GiftRegistry.query.filter_by(tenant_id=tenant.id, user_id=user.id).all()
        return jsonify({"registries": [r.to_dict() for r in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@customer_flows_bp.post("/gift-registries")
@jwt_required()
@limiter.limit("10 per minute")
def create_gift_registry():
    try:
        tenant, user = _ctx()
        data = request.get_json(silent=True) or {}
        from gift_svc.gift_registry_service import GiftRegistryService

        registry = GiftRegistryService().create_registry(
            tenant_id=tenant.id,
            customer_email=user.email,
            registry_name=data["registry_name"],
            event_type=data.get("event_type"),
            event_date=data.get("event_date"),
            is_public=bool(data.get("is_public", True)),
            user_id=user.id,
        )
        return jsonify({"registry": registry.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@customer_flows_bp.post("/gift-registries/<slug>/items")
@jwt_required()
@limiter.limit("10 per minute")
def add_gift_registry_item(slug: str):
    try:
        tenant, user = _ctx()
        from gift.gift_registry import GiftRegistry
        from gift_svc.gift_registry_service import GiftRegistryService

        registry = GiftRegistry.query.filter_by(tenant_id=tenant.id, slug=slug).first()
        if registry is None:
            return jsonify({"error": "Registry not found."}), 404
        if (
            registry.user_id != user.id
            and registry.customer_email.lower() != user.email.lower()
        ):
            return jsonify({"error": "Permission denied."}), 403
        data = request.get_json(silent=True) or {}
        item = GiftRegistryService().add_item(
            tenant_id=tenant.id,
            registry_id=registry.id,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
