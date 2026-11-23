#!/usr/bin/env python3
"""Full-database financial integrity audit (all tenants, all historical rows).

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/audit_financial_integrity.py

Checks mathematical invariants on stored data, not on newly created test
orders: payments vs orders, commissions, refunds and reversals, invoices,
financial events, store credit balances, inventory and live FX markup.
"""

from __future__ import annotations

import os
import pathlib
import sys
from decimal import ROUND_HALF_UP, Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    sys.path.insert(0, str(ROOT / part))

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILURES.append(f"{name}: {detail}")
        print(f"FAIL  {name} — {detail}")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main() -> None:
    from orion.app import create_app
    from orion.extensions import db

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        from currency.currency_rate import CurrencyRate
        from currency_svc.currency_service import CurrencyService
        from store_credit.store_credit import StoreCredit, StoreCreditTransaction

        from catalog.product import Product
        from oms.warehouse import InventoryLevel
        from order.order import Order
        from payment.payment import Payment
        from payment.refund import Refund
        from platform_models.commission_ledger import PlatformCommissionLedger
        from platform_models.financial_event import FinancialEvent
        from platform_models.invoice import Invoice
        from tenant.tenant import Tenant

        tenants = Tenant.query.filter_by(deleted_at=None).all()
        totals = {"payments": Decimal(0), "refunds": Decimal(0),
                  "commission": Decimal(0), "reversals": Decimal(0)}

        for tenant in tenants:
            tid = tenant.id
            slug = tenant.slug
            orders = {o.id: o for o in Order.query.filter_by(tenant_id=tid).all()}
            payments = Payment.query.filter_by(tenant_id=tid).all()

            for p in payments:
                order = orders.get(p.order_id)
                if p.status == "completed" and order:
                    check(f"{slug} payment {p.public_id} matches order total",
                          money(p.amount) == money(order.total),
                          f"{p.amount} vs {order.total}")

            paid = [p for p in payments if p.status == "completed"]
            totals["payments"] += sum((money(p.amount) for p in paid), Decimal(0))
            paid_ids = {p.id for p in paid}

            for r in Refund.query.filter_by(tenant_id=tid).all():
                payment = next((p for p in payments if p.id == r.payment_id), None)
                totals["refunds"] += money(r.amount)
                check(f"{slug} refund {r.id} has provider id", bool(r.provider_refund_id))
                if payment:
                    check(f"{slug} refund {r.id} within payment",
                          money(r.amount) <= money(payment.amount),
                          f"{r.amount} > {payment.amount}")
                events = FinancialEvent.query.filter_by(
                    tenant_id=tid, source_entity="refund", source_id=r.id
                ).all()
                check(f"{slug} refund {r.id} has negative event",
                      any(money(e.amount) == -money(r.amount) for e in events),
                      f"events={[str(e.amount) for e in events]}")

            for e in FinancialEvent.query.filter_by(tenant_id=tid).all():
                if e.status != "completed":
                    continue
                if e.source_entity == "refund" or "refund" in (e.event_type or ""):
                    check(f"{slug} refund event {e.id} negative", money(e.amount) < 0,
                          str(e.amount))
                elif e.direction == "inbound" or e.source_entity == "payment":
                    check(f"{slug} inbound event {e.id} positive", money(e.amount) > 0,
                          str(e.amount))

            ledger = PlatformCommissionLedger.query.filter_by(tenant_id=tid).all()
            by_id = {x.id: x for x in ledger}
            for x in ledger:
                if x.entry_type == "commission":
                    expected = (money(x.gross_amount) * Decimal(str(x.commission_percent))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    totals["commission"] += money(x.commission_amount)
                    check(f"{slug} commission {x.id}", money(x.commission_amount) == expected,
                          f"{x.commission_amount} vs {expected}")
                    check(f"{slug} commission {x.id} links completed payment",
                          x.payment_id in paid_ids)
                elif "reversal" in (x.entry_type or ""):
                    totals["reversals"] += money(x.commission_amount)
                    original = by_id.get(x.reverses_ledger_id)
                    check(f"{slug} reversal {x.id} references original", original is not None)
                    check(f"{slug} reversal {x.id} is negative", money(x.commission_amount) < 0,
                          str(x.commission_amount))
                    if original:
                        refund = Refund.query.filter_by(tenant_id=tid, payment_id=original.payment_id).first()
                        payment = next((p for p in payments if p.id == original.payment_id), None)
                        if refund and payment and money(payment.amount) > 0:
                            ratio = money(refund.amount) / money(payment.amount)
                            expected = -(money(original.commission_amount) * ratio).quantize(
                                Decimal("0.01"), rounding=ROUND_HALF_UP
                            )
                            check(f"{slug} reversal {x.id} amount", money(x.commission_amount) == expected,
                                  f"{x.commission_amount} vs {expected}")

            for inv in Invoice.query.filter_by(tenant_id=tid).all():
                order = orders.get(inv.order_id)
                if order:
                    check(f"{slug} invoice {inv.invoice_number} matches order",
                          money(inv.total_amount) == money(order.total),
                          f"{inv.total_amount} vs {order.total}")
                check(f"{slug} invoice {inv.invoice_number} has PDF",
                      bool(inv.storage_key or inv.pdf_artifact_path))

            for credit in StoreCredit.query.filter_by(tenant_id=tid).all():
                txns = StoreCreditTransaction.query.filter_by(credit_id=credit.id).all()
                net = sum(
                    (money(t.amount) if t.transaction_type == "credit" else -money(t.amount)
                     for t in txns),
                    Decimal(0),
                )
                check(f"{slug} credit {credit.id} balance", money(credit.balance) == net,
                      f"{credit.balance} vs {net}")

            for product in Product.query.filter_by(tenant_id=tid).all():
                total = sum(
                    (Decimal(str(row.quantity or 0)) for row in InventoryLevel.query.filter_by(
                        tenant_id=tid, product_id=product.id
                    ).all()),
                    Decimal(0),
                )
                check(f"{slug} stock {product.slug}", int(total) == int(product.quantity),
                      f"levels={total} product={product.quantity}")

        markup = Decimal(str(app.config.get("CURRENCY_FX_MARKUP_PERCENT", 0)))
        fx = CurrencyService()
        for row in CurrencyRate.query.all():
            if row.from_currency == row.to_currency:
                continue
            info = fx.rate_info(row.from_currency, row.to_currency)
            if info:
                expected = (Decimal(info["rate"]) * (Decimal(1) + markup / 100)).quantize(
                    Decimal("0.00000001")
                )
                check(f"FX markup {row.from_currency}->{row.to_currency}",
                      abs(Decimal(info["customer_rate"]) - expected) < Decimal("0.0000001"),
                      f"{info['customer_rate']} vs {expected}")

        # Cross-tenant aggregates
        check("commission is 1% of gross payments",
              abs(totals["commission"] - (totals["payments"] * Decimal("0.01")).quantize(Decimal("0.01"))) < Decimal("1"),
              f"commission={totals['commission']} payments={totals['payments']}")
        check("refunds do not exceed payments", totals["refunds"] <= totals["payments"],
              f"{totals['refunds']} vs {totals['payments']}")

        print(f"\nCHECKS: {CHECKS}  FAILURES: {len(FAILURES)}")
        print(f"GROSS PAYMENTS: {totals['payments']}")
        print(f"REFUNDS: {totals['refunds']}")
        print(f"NET REVENUE: {totals['payments'] - totals['refunds']}")
        print(f"COMMISSIONS: {totals['commission']}  REVERSALS: {totals['reversals']}")
        if FAILURES:
            for f in FAILURES:
                print(" -", f)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
