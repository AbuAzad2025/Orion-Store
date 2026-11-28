"""Round-13 regression: lifecycle transitions, middleware gate, recovery, audit."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _guard_not_live_db(database_url: str) -> None:
    url = database_url.lower()
    assert ":memory:" in url or "test" in url, f"non-test DB: {database_url!r}"


def _token(app, user) -> dict[str, str]:
    from flask_jwt_extended import create_access_token
    from support.http import bearer_headers

    with app.app_context():
        token = create_access_token(identity=str(user.public_id))
    return bearer_headers(token)


def _create(client, app, admin, *, slug, status=None, domain=None):
    payload = {"name": slug, "slug": slug, "email": f"{slug}@test.com"}
    if status:
        payload["status"] = status
    if domain:
        payload["domain"] = domain
    return client.post("/api/v1/tenants/", headers=_token(app, admin), json=payload)


def _set_status(client, app, admin, tenant_id, status):
    return client.put(
        f"/api/v1/tenants/{tenant_id}",
        headers=_token(app, admin),
        json={"status": status},
    )


def test_transition_matrix_is_enforced_in_service(app):
    from core.exceptions import ValidationError
    from tenant_svc.tenant_service import TenantService

    check = TenantService.validate_status_transition
    for current, target in (
        ("pending", "trial"),
        ("trial", "active"),
        ("trial", "suspended"),
        ("active", "suspended"),
        ("suspended", "active"),
        ("suspended", "cancelled"),
        ("active", "active"),
    ):
        check(current, target)
    for current, target in (
        ("active", "trial"),
        ("active", "pending"),
        ("trial", "pending"),
        ("cancelled", "active"),
        ("suspended", "pending"),
    ):
        with pytest.raises(ValidationError):
            check(current, target)
    check("cancelled", "active", allow_restore=True)
    with pytest.raises(ValidationError):
        check("active", "bogus")


def test_invalid_transition_rejected_by_api_and_noop_allowed(
    client, app, platform_admin
):
    created = _create(client, app, platform_admin, slug="transition-api")
    assert created.status_code == 201
    tenant_id = created.get_json()["tenant"]["id"]
    assert (
        _set_status(client, app, platform_admin, tenant_id, "cancelled").status_code
        == 200
    )
    blocked = _set_status(client, app, platform_admin, tenant_id, "active")
    assert blocked.status_code == 400
    assert "transition" in blocked.get_json()["error"]
    assert (
        _set_status(client, app, platform_admin, tenant_id, "cancelled").status_code
        == 200
    )


def test_suspended_store_is_403_for_api_and_404_for_storefront(
    client, app, platform_admin
):
    created = _create(client, app, platform_admin, slug="suspended-store")
    tenant_id = created.get_json()["tenant"]["id"]
    assert (
        _set_status(client, app, platform_admin, tenant_id, "suspended").status_code
        == 200
    )
    assert client.get("/api/v1/store/products").status_code == 404
    assert (
        client.get(
            "/api/v1/store/products", headers={"X-Tenant-ID": "suspended-store"}
        ).status_code
        == 403
    )
    assert client.get("/s/suspended-store/").status_code == 404
    assert (
        client.get(
            "/api/v1/tenants/me", headers={"X-Tenant-ID": "suspended-store"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/tenants/{tenant_id}", headers=_token(app, platform_admin)
        ).status_code
        == 200
    )


def test_cancelled_store_blocked_and_reactivate_suspended_only(
    client, app, platform_admin
):
    created = _create(client, app, platform_admin, slug="cancelled-store")
    tenant_id = created.get_json()["tenant"]["id"]
    assert (
        _set_status(client, app, platform_admin, tenant_id, "cancelled").status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/store/products", headers={"X-Tenant-ID": "cancelled-store"}
        ).status_code
        == 403
    )
    wrong = client.post(
        f"/api/v1/tenants/{tenant_id}/reactivate", headers=_token(app, platform_admin)
    )
    assert wrong.status_code == 400


def test_reactivate_restore_and_audit_entries(client, app, platform_admin):
    from platform_models.audit_log import AuditLog
    from tenant.tenant import Tenant
    from user.user import User

    with app.app_context():
        admin_id = (
            User.query.filter_by(email="owner@azadexa.com", tenant_id=None).first().id
        )
    created = _create(client, app, platform_admin, slug="revive-store")
    tenant_id = created.get_json()["tenant"]["id"]
    assert (
        _set_status(client, app, platform_admin, tenant_id, "suspended").status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/reactivate",
            headers=_token(app, platform_admin),
        ).status_code
        == 200
    )
    assert (
        _set_status(client, app, platform_admin, tenant_id, "cancelled").status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/restore", headers=_token(app, platform_admin)
        ).status_code
        == 200
    )
    with app.app_context():
        tenant = Tenant.query.get(tenant_id)
        assert tenant.status == "active" and tenant.is_active is True
        assert (
            AuditLog.query.filter_by(
                action="tenant.reactivated", resource_id=str(tenant_id)
            )
            .one()
            .actor_user_id
            == admin_id
        )
        assert (
            AuditLog.query.filter_by(
                action="tenant.restored", resource_id=str(tenant_id)
            )
            .one()
            .actor_user_id
            == admin_id
        )


def test_single_active_palestinian_heritage_store_stays_reachable(
    client, app, platform_admin
):
    created = _create(
        client, app, platform_admin, slug="palestinian-heritage", status="active"
    )
    assert created.status_code == 201
    assert (
        client.get(
            "/api/v1/tenants/me", headers={"X-Tenant-ID": "palestinian-heritage"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/store/products", headers={"X-Tenant-ID": "palestinian-heritage"}
        ).status_code
        == 200
    )
    assert client.get("/s/palestinian-heritage/").status_code == 200
