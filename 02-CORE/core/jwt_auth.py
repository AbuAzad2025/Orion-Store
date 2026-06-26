"""JWT token helpers (§0.5, §3.5)."""

from __future__ import annotations

from typing import Any

from flask_jwt_extended import create_access_token, create_refresh_token

from user.user import User


def issue_tokens_for_user(user: User) -> dict[str, str]:
    identity = str(user.public_id)
    claims: dict[str, Any] = {
        "is_superuser": user.is_superuser,
        "tenant_id": user.tenant_id,
    }
    return {
        "access_token": create_access_token(
            identity=identity, additional_claims=claims
        ),
        "refresh_token": create_refresh_token(
            identity=identity, additional_claims=claims
        ),
    }
