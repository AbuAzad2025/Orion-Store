"""RBAC helpers (§3.5).

Permission checks resolve through ``user_roles → role_permissions →
permissions``. Legacy boolean flags are kept only as compatibility shortcuts:

* superusers always pass (platform admins live outside the RBAC tables);
* tenant admins (``is_admin``) implicitly pass every ``tenant.*`` code even
  before roles are seeded for their account;
* customers are least-privileged — only explicitly granted ``store.*`` codes
  count for them.
"""

from __future__ import annotations

from core.context import get_user
from core.exceptions import AuthorizationError
from orion.extensions import db


def _granted_permission_codes(user) -> set[str]:
    """Permission codes granted to ``user`` through tenant-scoped roles.

    Joining ``roles`` and filtering on ``Role.tenant_id == user.tenant_id``
    is deliberate: a stray ``user_roles`` row pointing at a role owned by a
    different tenant must never grant anything.
    """
    if user.tenant_id is None:
        return set()

    # Deferred import avoids a core ↔ models import cycle at module load.
    from user.role import Permission, Role, RolePermission, UserRole

    rows = (
        db.session.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .filter(Role.tenant_id == user.tenant_id)
        .all()
    )
    return {code for (code,) in rows}


def user_has_permission(code: str) -> bool:
    user = get_user()
    if not user:
        return False
    if user.is_superuser:
        return True

    granted = _granted_permission_codes(user)

    if user.is_admin:
        # Increased compatibility: tenant admins own every tenant.* action.
        return code.startswith("tenant.") or code in granted

    # Customers: explicit store.* grants only, nothing implicit.
    return code.startswith("store.") and code in granted


def require_permission(code: str) -> None:
    if not user_has_permission(code):
        raise AuthorizationError(f"Missing permission: {code}")
