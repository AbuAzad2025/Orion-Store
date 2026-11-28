# ADR 0003 — Revoked-token identity stays a validated soft string

- **Status:** Accepted
- **Date:** 2026-11-28
- **Baseline:** `74f40f0` (Round 13)
- **Supersedes:** deferral "FK for revoked_tokens.user_public_id" — **NEVER-APPLY (closed)**

## Context

`users.public_id` is a native `UUID`. `revoked_tokens.user_public_id` is a
nullable `VARCHAR(64)` with no FK. JWT identities are normally user UUIDs but
legacy/anonymous identities (e.g. `cookie-user`, app `client_id`) are real and
supported. Adding a DB FK would require a destructive type conversion and
cleanup of non-UUID rows on the live store.

## Decision

1. Never add the DB FK; the deferral is closed as Won't-do. Reopening requires
   a new ADR.
2. Application guard in `core/jwt_auth.py::_revoke`: persist only a canonical
   UUID in `user_public_id`; everything else fails closed to `NULL`.
3. The JTI is **always** blocklisted — the guard constrains the identity
   column, not revocation itself.
4. No model or migration changes.

## Limits

The column remains `VARCHAR(64)`; the DB cannot enforce the invariant. Every
writer must go through `_revoke`.

## Consequences

Zero live migration; no dangling identity strings; legacy/anonymous logouts
still revoke their tokens.
