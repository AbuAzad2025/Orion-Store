"""Stripe Connect integration boundary (wave 4 #42)."""

from __future__ import annotations

from decimal import Decimal

from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway


def charge_stripe(
    *,
    order: Order,
    gateway: TenantPaymentGateway,
    amount: Decimal,
) -> dict:
    """Sandbox/test charge — replace with real Stripe SDK in production."""
    if gateway.is_sandbox:
        return {
            "success": True,
            "provider_payment_id": f"pi_test_{order.id}",
        }
    if not gateway.credentials_encrypted:
        return {"success": False, "error": "missing_credentials"}
    return {
        "success": True,
        "provider_payment_id": f"pi_live_{order.id}",
    }
