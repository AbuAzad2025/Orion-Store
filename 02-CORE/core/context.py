"""Request-scoped context on Flask `g`."""

from __future__ import annotations

from flask import g

from tenant.tenant import Tenant
from user.user import User


def get_tenant_id() -> int | None:
    return getattr(g, "tenant_id", None)


def get_tenant() -> Tenant | None:
    return getattr(g, "tenant", None)


def get_user() -> User | None:
    return getattr(g, "user", None)


def get_locale() -> str:
    return getattr(g, "locale", "ar")


def is_platform_admin() -> bool:
    user = get_user()
    return bool(user and user.is_superuser)
