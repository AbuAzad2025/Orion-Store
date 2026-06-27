"""Wave 5 tenant portal API tests."""

from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant_admin_store(app):
    tenant = TenantService().create_tenant(
        name="Portal Store", slug="portal-store", email="portal@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@portal.com",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def test_tenant_dashboard_api(client, tenant_admin_store):
    tenant, admin = tenant_admin_store
    headers = auth_headers(admin, tenant_id=tenant.slug)
    resp = client.get("/api/v1/tenant/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["stats"]["orders_total"] == 0


def test_tenant_gateways_and_templates(client, tenant_admin_store):
    tenant, admin = tenant_admin_store
    headers = auth_headers(admin, tenant_id=tenant.slug)

    cod = client.post("/api/v1/tenant/gateways/cod", headers=headers)
    assert cod.status_code == 201

    gateways = client.get("/api/v1/tenant/gateways", headers=headers)
    assert gateways.status_code == 200
    assert len(gateways.get_json()["gateways"]) == 1

    save = client.put(
        "/api/v1/tenant/document-templates/invoice",
        headers=headers,
        json={
            "body_html": (
                "<div>{{order_number}}</div>"
                '<footer id="azadexa-platform-footer" data-immutable="true"></footer>'
            ),
            "locale": "ar",
        },
    )
    assert save.status_code == 200

    listed = client.get("/api/v1/tenant/document-templates", headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()["templates"]) == 1
