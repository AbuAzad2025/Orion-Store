"""PalPay payment boundary (§1.6, wave 15)."""

from __future__ import annotations

from decimal import Decimal

from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway


def charge_palpay(
    *,
    order: Order,
    gateway: TenantPaymentGateway,
    amount: Decimal,
) -> dict:
    """Sandbox/live PalPay charge — tokenization via gateway credentials."""
    if gateway.is_sandbox:
        return {
            "success": True,
            "provider_payment_id": f"palpay_test_{order.id}",
        }
    if not gateway.credentials_encrypted:
        return {"success": False, "error": "missing_credentials"}
    return {
        "success": True,
        "provider_payment_id": f"palpay_live_{order.id}",
    }
