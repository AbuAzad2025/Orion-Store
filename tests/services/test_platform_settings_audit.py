"""Platform settings persistence + automatic audit coverage."""

from __future__ import annotations

import logging


def _admin_id(app) -> int:
    from user.user import User

    with app.app_context():
        user = User.query.filter_by(email="owner@azadexa.com", tenant_id=None).first()
        assert user is not None
        return user.id


def _seed_settings(app) -> None:
    from platform_svc.platform_settings_service import PlatformSettingsService

    with app.app_context():
        PlatformSettingsService().ensure_seeded()


def test_new_settings_fields_round_trip(app, client, platform_admin_headers):
    """The three new columns are writable via API and persisted/read back."""
    _seed_settings(app)
    payload = {
        "platform_name": "Azadexa",
        "owner_name": "Ahmad Ghannam",
        "support_email": "support@azadexa.test",
        "default_currency": "ILS",
        "default_language": "ar",
    }

    saved = client.put(
        "/api/v1/platform/settings", headers=platform_admin_headers, json=payload
    )
    assert saved.status_code == 200
    body = saved.get_json()["settings"]
    assert body["support_email"] == "support@azadexa.test"
    assert body["default_currency"] == "ILS"
    assert body["default_language"] == "ar"

    loaded = client.get("/api/v1/platform/settings", headers=platform_admin_headers)
    assert loaded.status_code == 200
    stored = loaded.get_json()["settings"]
    assert stored["support_email"] == "support@azadexa.test"
    assert stored["default_currency"] == "ILS"
    assert stored["default_language"] == "ar"

    from platform_models.platform_settings import PlatformSettings

    with app.app_context():
        row = PlatformSettings.query.filter_by(singleton="1").first()
        assert row.support_email == "support@azadexa.test"
        assert row.default_currency == "ILS"
        assert row.default_language == "ar"
        assert row.to_dict()["support_email"] == "support@azadexa.test"


def test_settings_seed_includes_new_fields(app):
    from platform_svc.platform_settings_service import PlatformSettingsService

    with app.app_context():
        row = PlatformSettingsService().ensure_seeded()
        assert row.support_email == "support@azadexa.com"
        assert row.default_currency == "ILS"
        assert row.default_language == "ar"


def test_platform_settings_update_is_audited(app, client, platform_admin_headers):
    """platform.settings.updated is logged automatically with the g.user actor."""
    _seed_settings(app)
    admin_id = _admin_id(app)

    resp = client.put(
        "/api/v1/platform/settings",
        headers=platform_admin_headers,
        json={"support_email": "audit@azadexa.test"},
    )
    assert resp.status_code == 200

    from platform_models.audit_log import AuditLog

    with app.app_context():
        row = (
            AuditLog.query.filter_by(action="platform.settings.updated")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert row is not None
        assert row.resource_type == "platform_settings"
        assert row.actor_user_id == admin_id
        assert "support_email" in row.details["fields"]


def test_tenant_created_is_audited(app, client, platform_admin_headers):
    """tenant.created is logged automatically with the g.user actor."""
    admin_id = _admin_id(app)

    resp = client.post(
        "/api/v1/tenants/",
        headers=platform_admin_headers,
        json={
            "name": "Audited Store",
            "slug": "audited-store",
            "email": "audited@store.test",
        },
    )
    assert resp.status_code == 201
    tenant_id = resp.get_json()["tenant"]["id"]

    from platform_models.audit_log import AuditLog

    with app.app_context():
        row = AuditLog.query.filter_by(
            action="tenant.created", resource_id=str(tenant_id)
        ).first()
        assert row is not None
        assert row.resource_type == "tenant"
        assert row.tenant_id == tenant_id
        assert row.actor_user_id == admin_id


def test_dns_failure_does_not_leave_half_created_tenant(app, monkeypatch, caplog):
    """A failing DNS registry is warned about and never fails tenant creation."""
    from integrations import external_registry

    def _boom(*, slug: str, tenant_id: int) -> dict:
        raise RuntimeError("DNS registry unavailable")

    monkeypatch.setattr(external_registry, "register_tenant_subdomain", _boom)

    # caplog depends on root handlers, which other tests reconfigure; spy on the
    # service logger directly so this assertion is order-independent.
    from tenant_svc import tenant_service as tenant_service_module

    warnings: list[str] = []
    monkeypatch.setattr(
        tenant_service_module.logger,
        "warning",
        lambda message, *args: warnings.append(
            str(message) % args if args else str(message)
        ),
    )

    from platform_models.audit_log import AuditLog
    from tenant.tenant import Tenant
    from tenant_svc.tenant_service import TenantService

    with caplog.at_level(logging.WARNING):
        with app.app_context():
            tenant = TenantService().create_tenant(
                name="DNS Failure Store",
                slug="dns-failure-store",
                email="dns@store.test",
            )
            assert tenant.id is not None

            persisted = Tenant.query.filter_by(slug="dns-failure-store").first()
            assert persisted is not None
            assert persisted.config is not None  # fully seeded, not half created

            audit = AuditLog.query.filter_by(
                action="tenant.created", resource_id=str(tenant.id)
            ).first()
            assert audit is not None

    assert any("Subdomain registration failed" in message for message in warnings)


def test_audit_api_ignores_client_supplied_actor(app, client, platform_admin_headers):
    """user_id/generated_by sent by a client never win over g.user.id."""
    admin_id = _admin_id(app)

    log = client.post(
        "/api/v1/audit/logs",
        headers=platform_admin_headers,
        json={"action": "manual.check", "user_id": 999999, "generated_by": 999999},
    )
    assert log.status_code == 201

    report = client.post(
        "/api/v1/audit/reports",
        headers=platform_admin_headers,
        json={"report_type": "manual", "generated_by": 999999, "summary": {}},
    )
    assert report.status_code == 201

    from audit.audit_v2 import PlatformAdminAuditLog, PlatformAuditReport

    with app.app_context():
        audit = PlatformAdminAuditLog.query.order_by(
            PlatformAdminAuditLog.id.desc()
        ).first()
        assert audit.user_id == admin_id

        generated = PlatformAuditReport.query.order_by(
            PlatformAuditReport.id.desc()
        ).first()
        assert generated.generated_by == admin_id
