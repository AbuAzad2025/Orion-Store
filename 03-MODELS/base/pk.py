"""Primary key type — ``BIGINT`` on PostgreSQL (production + CI tests)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer

# SQLite variant exists only for USE_SQLITE_TESTS=1 emergency fallback — not used in CI.
PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")
