"""Store admins must never reach platform pages/APIs, even cross-domain."""

from __future__ import annotations

from support.http import tenant_headers

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService

PLATFORM_PATHS_HTML = (
    "/admin/platform/dashboard",
    "/admin/platform/tenants",
    "/admin/platform/users",
    "/admin/platform/settings",
    "/admin/platform/audit",
    "/admin/platform/reconciliation",
)
PLATFORM_APIS = (
    "/api/v1/platform/stats",
    "/api/v1/tenants/",
    "/api/v1/users/",
    "/api/v1/platform/settings",
    "/api/v1/platform/reconciliation",
)


def _store_admin_headers(app, client, slug: str) -> dict[str, str]:
    from support.http import auth_headers

    from orion.extensions import db

    with app.app_context():
        from tenant.tenant import Tenant
        from user.user import User

        tenant = Tenant.query.filter_by(slug=slug).first()
        admin = User.query.filter_by(
            tenant_id=tenant.id, is_admin=True, is_superuser=False, deleted_at=None
        ).first()
        if admin is None:
            admin = AuthService().register_tenant_user(
                tenant_id=tenant.id,
                email="scope-admin@test.local",
                password="password123",
                is_admin=True,
            )
        h = auth_headers(admin, app=app, tenant_id=slug)
    return h


def test_store_admin_cannot_reach_platform_html(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(name="Scope", slug="scope", email="s@test.com")
    h = _store_admin_headers(app, client, "scope")
    for path in PLATFORM_PATHS_HTML:
        resp = client.get(path, headers={**h, "Host": "orion.azadexa.com"})
        assert resp.status_code in (302, 401, 403), path


def test_store_admin_cannot_reach_platform_apis(client, app) -> None:
    with app.app_context():
        TenantService().create_tenant(name="Scope2", slug="scope2", email="s2@test.com")
    h = _store_admin_headers(app, client, "scope2")
    for path in PLATFORM_APIS:
        resp = client.get(path, headers={**h, "Host": "orion.azadexa.com"})
        assert resp.status_code in (401, 403), (path, resp.status_code)


def test_platform_admin_token_required_for_platform_stats(client, app) -> None:
    resp = client.get("/api/v1/platform/stats", headers={"Host": "orion.azadexa.com"})
    assert resp.status_code in (401, 403)
