#!/usr/bin/env python3
"""End-to-end accounting verification on a seeded tenant.

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/verify_accounting_flow.py [slug]

Performs a real checkout, payment, partial refund and asserts the resulting
ledger/inventory/credit/currency invariants. Prints PASS/FAIL per check.
"""

from __future__ import annotations

import os
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    sys.path.insert(0, str(ROOT / part))

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    detail = detail.replace("→", "->")
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" - {detail}" if detail else ""))


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "outlet"
    os.environ.setdefault("FLASK_ENV", "development")
    from orion.app import create_app
    from orion.extensions import db

    app = create_app(os.environ["FLASK_ENV"])
    with app.app_context():
        from catalog.product import Product
        from currency_svc.currency_service import CurrencyService
        from oms.warehouse import InventoryLevel
        from order.order import Order
        from order_svc.cart_service import CartService
        from order_svc.checkout_service import CheckoutService
        from payment.payment import Payment
        from payment.refund import Refund
        from payment_svc.payment_service import PaymentService
        from platform_models.commission_ledger import PlatformCommissionLedger
        from platform_models.financial_event import FinancialEvent
        from platform_models.invoice import Invoice
        from platform_svc.pdf_service import get_invoice_storage
        from store_credit.store_credit import StoreCreditTransaction
        from store_credit_svc.store_credit_service import StoreCreditService
        from tenant.tenant import Tenant
        from user.user import User

        import uuid

        from auth.auth_service import AuthService

        tenant = Tenant.query.filter_by(slug=slug).first()
        if tenant is None:
            raise SystemExit(f"Tenant '{slug}' not found — run seed_demo_data.py first")
        # Fresh customer so pre-seeded credit cannot fully pay the order.
        customer = AuthService().register_tenant_user(
            tenant_id=tenant.id,
            email=f"verify-{uuid.uuid4().hex[:8]}@{slug}.test",
            password="password123",
            is_admin=False,
        )
        product = Product.query.filter_by(tenant_id=tenant.id, is_published=True).first()

        # --- store credit top-up -------------------------------------------
        credit_svc = StoreCreditService()
        credit = credit_svc.add_funds(
            tenant_id=tenant.id,
            customer_email=customer.email,
            amount="100",
            reason="accounting verification",
        )
        before_balance = Decimal(str(credit.balance))
        check("store credit top-up", before_balance >= Decimal("100"), str(before_balance))

        # --- checkout + payment --------------------------------------------
        qty = 2
        stock_before = product.quantity
        cart = CartService().get_or_create_cart(tenant_id=tenant.id)
        CartService().add_item(cart=cart, product_id=product.id, quantity=qty)
        order = CheckoutService().checkout(
            cart=cart,
            customer_email=customer.email,
            user_id=customer.id,
            is_guest=False,
            shipping_address={"city": "Test", "country_code": tenant.country_code},
            use_store_credit=True,
        )
        pay = PaymentService().pay_order(
            tenant_id=tenant.id,
            order_public_id=str(order.public_id),
            payment_method="cod",
        )
        payment = Payment.query.filter_by(tenant_id=tenant.id, order_id=order.id).first()
        check("order created", order.total is not None, order.order_number)
        check("payment completed", payment is not None and payment.status == "completed", str(payment.amount if payment else None))
        check("payment matches order total", Decimal(str(payment.amount)) == Decimal(str(order.total)), f"{payment.amount} vs {order.total}")

        # store credit was used at checkout
        after_credit = StoreCreditService().get_balance(
            tenant_id=tenant.id, customer_email=customer.email
        )
        check("store credit debited at checkout", after_credit < before_balance, f"{before_balance} -> {after_credit}")
        txn = StoreCreditTransaction.query.filter_by(
            tenant_id=tenant.id, credit_id=credit.id, transaction_type="debit"
        ).first()
        check("store credit transaction recorded", txn is not None, str(txn.amount if txn else None))

        # --- invoice + PDF ---------------------------------------------------
        invoice = Invoice.query.filter_by(tenant_id=tenant.id, order_id=order.id).first()
        check("invoice created", invoice is not None, str(invoice.invoice_number if invoice else None))
        if invoice:
            db.session.refresh(invoice)
            key = invoice.storage_key or invoice.pdf_artifact_path
            stored = None
            if key:
                try:
                    stored = get_invoice_storage().get(key)
                except Exception:
                    stored = None
            check("invoice PDF stored", bool(stored), str(key))

        # --- financial event + commission -----------------------------------
        inbound = FinancialEvent.query.filter_by(
            tenant_id=tenant.id, source_entity="payment", source_id=payment.id
        ).first()
        check("inbound financial event", inbound is not None and inbound.status == "completed", str(inbound.amount if inbound else None))
        ledger = PlatformCommissionLedger.query.filter_by(
            tenant_id=tenant.id, payment_id=payment.id, entry_type="commission"
        ).first()
        expected_commission = (Decimal(str(payment.amount)) * ledger.commission_percent).quantize(Decimal("0.01")) if ledger else Decimal("0")
        check("commission ledger booked", ledger is not None and Decimal(str(ledger.commission_amount)) == expected_commission, f"{ledger.commission_amount if ledger else None} expected {expected_commission}")

        # --- inventory --------------------------------------------------------
        db.session.refresh(product)
        check("product stock decremented", product.quantity == stock_before - qty, f"{stock_before} -> {product.quantity}")
        total_levels = (
            db.session.query(db.func.coalesce(db.func.sum(InventoryLevel.quantity), 0))
            .filter(InventoryLevel.tenant_id == tenant.id, InventoryLevel.product_id == product.id)
            .scalar()
        )
        check("warehouse stock sums to product total", int(total_levels) == product.quantity, f"levels={total_levels} product={product.quantity}")

        # --- partial refund + reversal ---------------------------------------
        refund_amount = Decimal("10.00")
        PaymentService().refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=refund_amount,
            reason="accounting verification partial",
        )
        refund = Refund.query.filter_by(tenant_id=tenant.id, payment_id=payment.id).first()
        check("refund row created", refund is not None and Decimal(str(refund.amount)) == refund_amount, str(refund.amount if refund else None))
        check("provider refund id set", bool(refund and refund.provider_refund_id), str(refund.provider_refund_id if refund else None))
        outbound = FinancialEvent.query.filter_by(
            tenant_id=tenant.id, source_entity="refund", source_id=refund.id
        ).first()
        check("negative refund event", outbound is not None and Decimal(str(outbound.amount)) == -refund_amount, str(outbound.amount if outbound else None))
        reversal = PlatformCommissionLedger.query.filter_by(
            tenant_id=tenant.id,
            reverses_ledger_id=ledger.id,
            entry_type="commission_reversal",
        ).first()
        ratio = refund_amount / Decimal(str(payment.amount))
        expected_reversal = -(Decimal(str(ledger.commission_amount)) * ratio).quantize(Decimal("0.01"))
        check("commission reversal posted", reversal is not None and Decimal(str(reversal.commission_amount)) == expected_reversal, f"{reversal.commission_amount if reversal else None} expected {expected_reversal}")
        db.session.refresh(order)
        check("partial refund keeps order paid", order.payment_status == "paid", order.payment_status)

        # --- FX with 3% customer markup -------------------------------------
        fx = CurrencyService()
        rate = fx.latest_rate("ILS", tenant.default_currency)
        info = fx.rate_info("ILS", tenant.default_currency)
        if rate and tenant.default_currency != "ILS":
            converted = fx.convert(
                amount=Decimal("100"),
                from_currency="ILS",
                to_currency=tenant.default_currency,
                markup_percent=app.config.get("CURRENCY_FX_MARKUP_PERCENT", 0),
            )
            expected = (Decimal("100") * rate * (Decimal(1) + Decimal(str(app.config.get("CURRENCY_FX_MARKUP_PERCENT", 0))) / 100)).quantize(Decimal("0.01"))
            check("FX conversion + markup", converted == expected, f"{converted} expected {expected}")
            check("FX info exposes markup", bool(info and info.get("customer_rate")), str(info))
        else:
            check("FX rate available", rate is not None, tenant.default_currency)

        failed = [n for n, ok, _ in RESULTS if not ok]
        print(f"\nSUMMARY: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
        if failed:
            print("FAILED:", ", ".join(failed))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
