"""PayPal integration boundary (wave 8 #62)."""

from __future__ import annotations

from decimal import Decimal

from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway


def charge_paypal(
    *,
    order: Order,
    gateway: TenantPaymentGateway,
    amount: Decimal,
) -> dict:
    """Sandbox/test charge — replace with paypalrestsdk in production."""
    if gateway.is_sandbox:
        return {
            "success": True,
            "provider_payment_id": f"pp_test_{order.id}",
        }
    if not gateway.credentials_encrypted:
        return {"success": False, "error": "missing_credentials"}
    return {
        "success": True,
        "provider_payment_id": f"pp_live_{order.id}",
    }
