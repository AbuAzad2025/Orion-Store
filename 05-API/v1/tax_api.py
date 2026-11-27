from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request
from tax_svc.tax_service import TaxService

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin, require_tenant_context

tax_bp = Blueprint("tax", __name__)
_svc = TaxService()


@tax_bp.route("/jurisdictions", methods=["GET"])
def list_jurisdictions():
    try:
        require_tenant_admin()
        return (
            jsonify(
                {
                    "jurisdictions": [
                        j.to_dict() for j in _svc.list_jurisdictions(g.tenant_id)
                    ]
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tax_bp.post("/calculate")
def calculate_tax():
    """Public (within tenant context) tax preview for a shipping address."""
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        shipping_cost = data.get("shipping_cost")
        tax = _svc.compute_tax(
            tenant_id=tenant.id,
            subtotal=Decimal(str(data.get("subtotal", "0"))),
            shipping_address=data.get("shipping_address") or {},
            shipping_cost=(
                Decimal(str(shipping_cost)) if shipping_cost is not None else None
            ),
        )
        return jsonify({"tax_amount": str(tax)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return jsonify({"error": "Invalid request."}), 400


@tax_bp.route("/jurisdictions", methods=["POST"])
def create_jurisdiction():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        j = _svc.create_jurisdiction(
            tenant_id=g.tenant_id,
            code=data["code"],
            name=data["name"],
            country_code=data["country_code"],
            region=data.get("region"),
        )
        return jsonify({"jurisdiction": j.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@tax_bp.route("/jurisdictions/<int:jurisdiction_id>/rates", methods=["POST"])
def set_rate(jurisdiction_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        from decimal import Decimal

        rate_value = Decimal(str(data["rate"]))
        if not rate_value.is_finite() or not (
            Decimal("0") <= rate_value < Decimal("1")
        ):
            raise ValidationError("Tax rate must be a fraction between 0 and 1.")
        rate = _svc.set_rate(
            tenant_id=g.tenant_id,
            jurisdiction_id=jurisdiction_id,
            rate=rate_value,
            product_tax_code=data.get("product_tax_code"),
            priority=int(data.get("priority", 0)),
        )
        return jsonify({"rate": rate.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
