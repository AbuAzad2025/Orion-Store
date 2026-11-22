# Accounting & workflow audit

Live verification was executed against the seeded demo database
(`orion_demo_live`) using `scripts/verify_accounting_flow.py`.

## Command

```powershell
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/orion_demo_live `
FLASK_ENV=development python scripts/verify_accounting_flow.py <slug>
```

The script performs a **real** purchase cycle per tenant and asserts the
resulting ledger state. It is safe to re-run: each run creates a fresh
verification customer and order.

## Checks performed

| # | Check | Meaning |
|---|-------|---------|
| 1 | store credit top-up | credit can be funded |
| 2 | order created | checkout succeeds |
| 3 | payment completed | COD gateway records payment |
| 4 | payment = order total | amount integrity |
| 5 | store credit debited | credit applied at checkout |
| 6 | credit transaction recorded | audit trail |
| 7 | invoice created | invoice row per order |
| 8 | invoice PDF stored | rendered PDF exists in storage |
| 9 | inbound financial event | money-in event posted |
| 10 | commission ledger booked | platform fee = amount × commission % |
| 11 | product stock decremented | catalogue quantity reduced |
| 12 | warehouse stock sums to product total | no double-counting across warehouses |
| 13 | refund row created | partial refund recorded |
| 14 | provider refund id set | gateway reference stored |
| 15 | negative refund event | money-out event posted |
| 16 | commission reversal posted | fee reversed pro-rata, negative entry |
| 17 | partial refund keeps order paid | order state not corrupted |
| 18 | FX conversion + markup | live rate × (1 + 3%) |
| 19 | FX info exposes markup | footer transparency data |

## Results (2026-11-22)

| Tenant | Currency | Result |
|--------|----------|--------|
| outlet | ILS | 18/18 (no FX conversion: same currency) |
| gulf | AED | 19/19 |
| euro | EUR | 19/19 |
| atlantic | USD | 19/19 |
| sterling | GBP | 19/19 |

**Total: 94/94 checks passed.**

## Defect found and fixed

The audit exposed a real inventory bug: `OmsService.sync_product_to_warehouse`
set a single warehouse's level equal to the whole product quantity. In a
two-warehouse tenant this double-counted stock (e.g. product 38 but levels
28 + 10 = 38 only after the fix; before it was 38 + 10 = 48).

Fix: the target warehouse now receives `product.quantity - sum(other
warehouses)`, so the sum of all warehouse levels always equals the sellable
catalogue quantity. Existing demo rows were repaired by re-syncing all 60
products. Single-warehouse behaviour is unchanged.

## Test evidence

- `tests/services/test_inventory_consistency.py` — passed
- `tests/services/test_coverage_final_services.py` — passed (28 tests total)
- `pre-commit run --all-files` — all hooks passed
