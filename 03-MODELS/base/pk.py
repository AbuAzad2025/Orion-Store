"""Primary key column compatible with SQLite (tests) and PostgreSQL (prod)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer

PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")
