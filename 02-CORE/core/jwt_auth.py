"""JWT token helpers (§0.5, §3.5)."""

from __future__ import annotations

from typing import Any

from flask import Response
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
)

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


def set_jwt_cookies(response: Response, tokens: dict[str, str]) -> Response:
    set_access_cookies(response, tokens["access_token"])
    set_refresh_cookies(response, tokens["refresh_token"])
    return response
