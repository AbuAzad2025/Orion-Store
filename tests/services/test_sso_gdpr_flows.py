"""SSO exchange and GDPR data-subject flows — real HTTP + real DB."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from orion.extensions import db

CLIENT_SECRET = "correct-horse-battery-staple"
SUBJECT_EMAIL = "subject@sso-gdpr.test"


def _create_tenant_and_admin(app) -> tuple[object, object]:
    from auth.auth_service import AuthService
    from tenant_svc.tenant_service import TenantService

    tenant = TenantService().create_tenant(
        name="SSO GDPR Tenant",
        slug="sso-gdpr-tenant",
        email="owner@sso-gdpr.test",
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@sso-gdpr.test",
        password="password123",
        is_admin=True,
    )
    return tenant, SimpleNamespace(public_id=str(admin.public_id), email=admin.email)


def _create_provider(app, tenant_id: int, *, is_active: bool = True):
    from compliance_svc.compliance_service import ComplianceService

    provider = ComplianceService().create_sso(
        tenant_id=tenant_id,
        provider_type="oidc",
        client_id="orion-client",
        client_secret=CLIENT_SECRET,
        issuer_url="https://idp.example.test",
    )
    if not is_active:
        provider.is_active = False
        db.session.commit()
    return provider


def _seed_subject(app, tenant_id: int, *, request_type: str):
    """Create a data request plus a user, an order and a consent record."""
    from auth.auth_service import AuthService
    from compliance_svc.compliance_service import ComplianceService
    from order.order import Order
    from user.user import User

    svc = ComplianceService()
    req = svc.create_data_request(
        tenant_id=tenant_id, customer_email=SUBJECT_EMAIL, request_type=request_type
    )
    user = User(
        tenant_id=tenant_id,
        email=SUBJECT_EMAIL,
        password_hash=AuthService().hash_password("password123"),
        is_customer=True,
    )
    order = Order(
        tenant_id=tenant_id,
        order_number="ORD-SSO-GDPR-1",
        customer_email=SUBJECT_EMAIL,
        customer_first_name="Subject",
        customer_last_name="Person",
    )
    db.session.add_all([user, order])
    svc.record_consent(
        tenant_id=tenant_id,
        customer_email=SUBJECT_EMAIL,
        consent_type="marketing",
        granted=True,
    )
    db.session.commit()
    return req, user, order


def test_sso_exchange_creates_user_and_returns_jwt(client, app):
    with app.app_context():
        tenant, _admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        provider = _create_provider(app, tenant_id)
        # A real salted hash is stored, never the raw secret or a random uuid.
        assert provider.client_secret_hash != CLIENT_SECRET
        assert len(provider.client_secret_hash) == 64

    response = client.post(
        "/api/v1/auth/sso/exchange",
        headers={"X-Tenant-ID": slug},
        json={
            "provider_code": CLIENT_SECRET,
            "external_email": "sso-user@sso-gdpr.test",
        },
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["user"]["email"] == "sso-user@sso-gdpr.test"
    assert data["user"]["tenant_id"] == tenant_id
    assert "access_token" in data and "refresh_token" in data

    with app.app_context():
        from user.user import User

        user = User.query.filter_by(
            tenant_id=tenant_id, email="sso-user@sso-gdpr.test"
        ).first()
        assert user is not None
        assert user.is_verified is True

    # Exchanging again reuses the same account instead of duplicating it.
    second = client.post(
        "/api/v1/auth/sso/exchange",
        headers={"X-Tenant-ID": slug},
        json={
            "token": CLIENT_SECRET,
            "external_email": "sso-user@sso-gdpr.test",
        },
    )
    assert second.status_code == 200
    with app.app_context():
        from user.user import User

        assert (
            User.query.filter_by(
                tenant_id=tenant_id, email="sso-user@sso-gdpr.test"
            ).count()
            == 1
        )


def test_sso_exchange_rejects_disabled_provider(client, app):
    with app.app_context():
        tenant, _admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        _create_provider(app, tenant_id, is_active=False)

    response = client.post(
        "/api/v1/auth/sso/exchange",
        headers={"X-Tenant-ID": slug},
        json={
            "provider_code": CLIENT_SECRET,
            "external_email": "blocked@sso-gdpr.test",
        },
    )
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_sso_exchange_rejects_wrong_code(client, app):
    with app.app_context():
        tenant, _admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        _create_provider(app, tenant_id)

    response = client.post(
        "/api/v1/auth/sso/exchange",
        headers={"X-Tenant-ID": slug},
        json={
            "provider_code": "not-the-client-secret",
            "external_email": "attacker@sso-gdpr.test",
        },
    )
    assert response.status_code == 401
    with app.app_context():
        from user.user import User

        assert (
            User.query.filter_by(
                tenant_id=tenant_id, email="attacker@sso-gdpr.test"
            ).first()
            is None
        )


def test_data_export_returns_subject_data(client, app):
    from support.http import auth_headers

    with app.app_context():
        tenant, admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        req, _user, _order = _seed_subject(app, tenant_id, request_type="access")
        request_id = req.id
        headers = auth_headers(admin, tenant_id=slug)

    response = client.post(
        f"/api/v1/compliance/data-requests/{request_id}/export", headers=headers
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["subject"]["email"] == SUBJECT_EMAIL
    assert data["user"]["email"] == SUBJECT_EMAIL
    assert any(o["order_number"] == "ORD-SSO-GDPR-1" for o in data["orders"])
    assert any(
        c["customer_email"] == SUBJECT_EMAIL for c in data["consent_records"]
    )


def test_execute_delete_anonymises_subject_data(client, app):
    from compliance.compliance import DataSubjectRequest
    from order.order import Order
    from support.http import auth_headers
    from user.user import User

    with app.app_context():
        tenant, admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        req, user, order = _seed_subject(app, tenant_id, request_type="erasure")
        request_id, user_id, order_id = req.id, user.id, order.id
        headers = auth_headers(admin, tenant_id=slug)

    response = client.post(
        f"/api/v1/compliance/data-requests/{request_id}/execute-delete",
        headers=headers,
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    result = response.get_json()
    assert result["request"]["status"] == "completed"
    assert result["users_anonymised"] == 1
    assert result["orders_anonymised"] == 1

    with app.app_context():
        req = db.session.get(DataSubjectRequest, request_id)
        assert req.status == "completed"
        assert req.completed_at is not None

        user = db.session.get(User, user_id)
        assert user.email != SUBJECT_EMAIL
        assert user.is_active is False
        assert user.deleted_at is not None
        assert user.first_name is None

        order = db.session.get(Order, order_id)
        assert order.customer_email != SUBJECT_EMAIL
        assert order.customer_first_name is None
        assert order.shipping_address == {}
        assert order.user_id is None

        assert (
            User.query.filter_by(tenant_id=tenant_id, email=SUBJECT_EMAIL).first()
            is None
        )


def test_data_export_requires_tenant_admin(client, app):
    with app.app_context():
        tenant, _admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        req, _user, _order = _seed_subject(app, tenant_id, request_type="access")
        request_id = req.id

    response = client.post(
        f"/api/v1/compliance/data-requests/{request_id}/export",
        headers={"X-Tenant-ID": slug},
    )
    assert response.status_code == 401


def test_storefront_consent_route_renders_banner(client, app):
    with app.app_context():
        tenant, _admin = _create_tenant_and_admin(app)
        tenant_id, slug = tenant.id, tenant.slug
        from compliance_svc.compliance_service import ComplianceService

        ComplianceService().upsert_cookie_settings(
            tenant_id=tenant_id,
            banner_message="نستخدم الكوكيز لتحسين الخدمة",
            is_active=True,
        )

    response = client.get("/consent", headers={"X-Tenant-ID": slug})
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_data(as_text=True)
    assert 'id="cookie-consent"' in body
    assert "نستخدم الكوكيز لتحسين الخدمة" in body
    assert 'lang="ar"' in body  # existing locale wiring is preserved
