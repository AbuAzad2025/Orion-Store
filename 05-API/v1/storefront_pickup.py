"""BOPIS storefront endpoints and checkout hook."""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from core.exceptions import OrionError
from core.middleware import require_tenant_context

storefront_pickup_bp = Blueprint("storefront_pickup", __name__)


@storefront_pickup_bp.get("/pickup-locations")
def list_pickup_locations():
    """Active BOPIS locations for the storefront (no admin auth required)."""
    try:
        tenant = require_tenant_context()
        from bopis.bopis import PickupLocation

        rows = PickupLocation.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        return jsonify({"locations": [r.to_dict() for r in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


def book_pickup_for_order(tenant_id: int, order, data: dict) -> dict | None:
    pickup_location_id = data.get("pickup_location_id")
    if not pickup_location_id:
        return None
    from bopis_svc.bopis_service import BopisService

    return BopisService().book_checkout(
        tenant_id=tenant_id,
        location_id=int(pickup_location_id),
        order_id=order.id,
    )
