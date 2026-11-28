# ADR 0002 — Financial soft links stay application-enforced

- **Status:** Accepted
- **Date:** 2026-11-28
- **Baseline:** `a4e2a0a` (Round 12)
- **Supersedes:** deferral "convert financial soft links to DB FKs" — **Won't-do (closed)**

## Context

`platform_commission_ledger.financial_event_id → financial_events.id` is a real
FK (`RESTRICT`, `UNIQUE`, NOT NULL). The reverse link
`financial_events.commission_ledger_id` is nullable with no FK, and
`financial_events.source_entity/source_id` is polymorphic (payment, refund,
order, commission_ledger). Adding a reverse FK would create a two-table cycle
with two `RESTRICT` edges, requiring two-phase writes and a live migration.
A polymorphic link cannot be a single SQL FK at all.

## Decision

1. Keep both soft links unconstrained by the database; writes remain
   application-enforced in the service layer.
2. The FK-conversion deferral is closed as **Won't-do**. Reopening requires a
   new ADR and a solved polymorphic design.
3. `scripts/audit_financial_integrity.py` is the compensating control: it
   checks event↔ledger, source resolution, payment/refund→event, reversal→
   original and invoice links in both directions.
4. Any new soft link in the money graph must be added to that audit in the
   same change.

## Known accepted limits

- Ledger→event backlink is asserted only when the event declares a
  `commission_ledger_id`; legacy unlabelled rows are skipped (Round 10 guard).
- `gateway_id`/`platform_gateway_id` are dormant (no writer, no FK) and are
  not audited; if populated, checks must be added with that change.

## Consequences

No cyclic FK, no delete deadlock, no live schema migration. PostgreSQL will
not reject a dangling soft link at write time; the full-DB audit must be run
as part of release verification.
