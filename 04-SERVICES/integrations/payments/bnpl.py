"""BNPL provider integration boundary (wave 8 #62)."""

from __future__ import annotations

from decimal import Decimal

from bnpl.bnpl_provider import BnplProvider
from order.order import Order


def charge_bnpl(
    *,
    order: Order,
    provider_row: BnplProvider,
    amount: Decimal,
) -> dict:
    """Authorize/capture BNPL — sandbox stub for Tabby/Tamara."""
    sandbox = bool((provider_row.config or {}).get("is_sandbox", True))
    if sandbox:
        return {
            "success": True,
            "external_transaction_id": f"bnpl_test_{provider_row.provider}_{order.id}",
            "installment_plan": {"installments": 4, "interval": "monthly"},
        }
    if not provider_row.api_credentials_encrypted:
        return {"success": False, "error": "missing_credentials"}
    return {
        "success": True,
        "external_transaction_id": f"bnpl_live_{provider_row.provider}_{order.id}",
        "installment_plan": {"installments": 4, "interval": "monthly"},
    }
