# Accounting & tax audit notes

## VAT / tax treatment of refunds (disclosure)

- Refunds are recorded at the **gross amount returned to the customer**, which
  includes the tax/VAT originally charged. The reversal is posted as one
  negative `payment.refund` financial event linked to the original inbound
  event by `reverses_financial_event_id` (see `PaymentService.refund` and
  `record_external_refund`). Platform commission is reversed separately and
  pro-rata by `CommissionService.reverse_for_payment`.
- The tax amount charged on a sale is snapshotted on `orders.tax_amount` at
  checkout (storefront or WhatsApp) and mirrored on the issued invoice. It is
  **not recomputed at refund time**, so it always reflects the rate in force
  when the sale occurred.
- **No VAT ledger, tax-authority integration, or credit-note document exists.**
  The platform does not issue tax credit notes, does not report VAT to any
  authority, and does not automatically reclaim or reverse VAT in a statutory
  sense. The `Refund` table intentionally has no VAT or credit-note fields.
- Confirming VAT liability adjustments (including issuing a credit note and
  reclaiming VAT on full or partial returns) is a **manual, off-platform
  accounting process** performed by the merchant in their own books, in
  accordance with their jurisdiction and registration status. Manual/WhatsApp
  sales are settled outside the platform, so the corresponding VAT adjustment
  is likewise handled outside it.
- Consequently, `SalesReportService.tax` reports tax charged on orders and is
  not reduced by refunds; it is a sales figure, not a filed VAT return. Merchants
  must not treat it as a tax declaration.

**Decision (Round-10):** Adding VAT/credit-note columns to `Refund` and
auto-reversing VAT on full refund is **deferred**. Rationale: no downstream
consumer, credit notes are legal documents requiring authority integration and
sequential issuance, VAT reclaim policy is jurisdiction/merchant specific, and
the existing gross refund + commission-reversal design is already internally
consistent and covered by regression tests. Revisit only when a VAT
export/authority integration and a merchant-supplied, jurisdiction-specific
reclaim policy exist; any such implementation should *derive* the VAT component
from `orders.tax_amount` and apply it idempotently across all three refund
entry points.

## Reconciliation invariants enforced by `scripts/audit_financial_integrity.py`

- Gross payments equal the sum of captured `completed` and `refunded` payments.
- Commission is 1% of gross captures; reversals are 1% of completed refunds;
  net commission is 1% of net revenue.
- Refund events are negative and link back to the refund row; commission
  reversals link to the original commission entry.
- `financial_events.source_entity/source_id` and `commission_ledger_id` are
  soft links checked by the audit because SQL FKs would create a cycle.
