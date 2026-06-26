"""RBAC helpers (§3.5)."""

from __future__ import annotations

from core.context import get_user
from core.exceptions import AuthorizationError


def user_has_permission(code: str) -> bool:
    user = get_user()
    if not user:
        return False
    if user.is_superuser:
        return True
    # Wave 1: expand with role_permissions query in wave 2
    return user.is_admin and code.startswith("tenant.")


def require_permission(code: str) -> None:
    if not user_has_permission(code):
        raise AuthorizationError(f"Missing permission: {code}")
