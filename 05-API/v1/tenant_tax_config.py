"""Tenant tax configuration API — /api/v1/tenant/tax-config."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin
from orion.extensions import db
from tenant.tenant_config import TenantConfig

tenant_tax_config_bp = Blueprint("tenant_tax_config", __name__)


def _config():
    config = TenantConfig.query.filter_by(tenant_id=g.tenant_id).first()
    if not config:
        config = TenantConfig(tenant_id=g.tenant_id)
        db.session.add(config)
        db.session.commit()
    return config


@tenant_tax_config_bp.get("/tax-config")
def get_tax_config():
    try:
        require_tenant_admin()
        config = _config()
        return (
            jsonify(
                {
                    "tax_config": {
                        "tax_rate": str(Decimal(str(config.tax_rate or 0)) * 100),
                        "tax_included": bool(config.tax_included),
                    }
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_tax_config_bp.put("/tax-config")
def update_tax_config():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        config = _config()
        if "tax_rate" in data:
            try:
                rate = Decimal(str(data["tax_rate"]))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValidationError("Invalid tax rate.") from exc
            if not rate.is_finite() or rate < 0 or rate > 100:
                raise ValidationError("Tax rate must be between 0 and 100.")
            config.tax_rate = rate / Decimal("100")
        if "tax_included" in data:
            config.tax_included = bool(data["tax_included"])
        db.session.commit()
        return (
            jsonify(
                {
                    "tax_config": {
                        "tax_rate": str(Decimal(str(config.tax_rate or 0)) * 100),
                        "tax_included": bool(config.tax_included),
                    }
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
