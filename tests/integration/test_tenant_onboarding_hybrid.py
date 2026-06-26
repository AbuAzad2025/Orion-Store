"""Hybrid integration template — live DB write + mocked gateway callback.

Copy this pattern for payments (wave 4), SMS, webhooks:
  1. Exercise the route via ``client`` (real Flask request stack).
  2. Assert rows in PostgreSQL via ``db_session`` (never mock the ORM).
  3. Stub outbound HTTP with ``mocker.patch.object`` on the integration client only.
"""

from __future__ import annotations

import pytest
import requests
from support.factories import tenant_create_payload
from support.http import auth_headers

from tenant.tenant import Tenant
from tenant.tenant_config import TenantConfig
from user.user import User

pytestmark = pytest.mark.integration


def test_tenant_onboarding_persists_to_postgres_and_stubs_gateway_callback(
    client, platform_admin, db_session, mocker
):
    """POST /tenants persists rows; outbound gateway HTTP is mocked."""
    gateway_response = mocker.Mock()
    gateway_response.raise_for_status = mocker.Mock()
    gateway_response.json.return_value = {
        "status": "provisioned",
        "callback_id": "cb_test_001",
    }
    gateway_post = mocker.patch.object(requests, "post", return_value=gateway_response)
    mocker.patch.dict(
        "os.environ",
        {"TENANT_REGISTRY_URL": "https://gateway.azadexa.test/v1"},
        clear=False,
    )

    response = client.post(
        "/api/v1/tenants/",
        headers=auth_headers(platform_admin),
        json=tenant_create_payload(
            name="Gateway Store",
            slug="gateway-store",
            email="gateway@store.com",
            admin_email="admin@gateway.com",
            admin_password="password123",
        ),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["tenant"]["slug"] == "gateway-store"

    tenant = db_session.query(Tenant).filter_by(slug="gateway-store").one()
    config = db_session.query(TenantConfig).filter_by(tenant_id=tenant.id).one()
    admin = (
        db_session.query(User)
        .filter_by(tenant_id=tenant.id, email="admin@gateway.com")
        .one()
    )

    assert config.business_name == "Gateway Store"
    assert admin.is_admin is True
    assert tenant.email == "gateway@store.com"

    gateway_post.assert_called_once()
    assert gateway_post.call_args.kwargs["json"] == {
        "slug": "gateway-store",
        "tenant_id": tenant.id,
    }
    assert "gateway.azadexa.test" in gateway_post.call_args.args[0]


def test_duplicate_slug_rejected_with_single_database_row(
    client, platform_admin, db_session, mocker
):
    mocker.patch.object(
        requests,
        "post",
        return_value=mocker.Mock(
            raise_for_status=mocker.Mock(),
            json=mocker.Mock(return_value={"status": "ok"}),
        ),
    )
    mocker.patch.dict(
        "os.environ",
        {"TENANT_REGISTRY_URL": "https://gateway.azadexa.test/v1"},
        clear=False,
    )
    headers = auth_headers(platform_admin)
    first = tenant_create_payload(slug="once-only", name="First", email="a@t.com")

    assert (
        client.post("/api/v1/tenants/", headers=headers, json=first).status_code == 201
    )
    duplicate = client.post(
        "/api/v1/tenants/",
        headers=headers,
        json=tenant_create_payload(
            slug="once-only",
            name="Second",
            email="b@t.com",
            admin_email=None,
            admin_password=None,
        ),
    )

    assert duplicate.status_code == 400
    assert db_session.query(Tenant).filter_by(slug="once-only").count() == 1


def test_postgresql_check_constraint_blocks_invalid_superuser(db_session):
    """CHECK constraint on superuser — PostgreSQL only (CI container)."""
    from sqlalchemy.exc import IntegrityError

    from auth.auth_service import AuthService

    admin = AuthService().register_super_admin(
        email="invalid-super@azadexa.com", password="password123"
    )
    admin.tenant_id = 999
    db_session.add(admin)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
