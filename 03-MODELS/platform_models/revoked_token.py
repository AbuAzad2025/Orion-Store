"""Server-side JWT revocation ledger (logout / security incidents)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from base.pk import PrimaryKeyType
from orion.extensions import db


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(
        PrimaryKeyType, primary_key=True, autoincrement=True
    )
    jti: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False, default="access")
    user_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )

    @classmethod
    def is_revoked(cls, jti: str | None) -> bool:
        if not jti:
            return False
        return cls.query.filter_by(jti=jti).first() is not None
