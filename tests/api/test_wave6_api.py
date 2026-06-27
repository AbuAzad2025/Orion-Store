"""Shipping and voucher API tests (wave 6)."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_shipping_api_create_and_calculate(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="API Ship", slug="api-ship", email="as@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@as.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    create = client.post(
        "/api/v1/shipping/methods",
        headers=headers,
        json={
            "name": "Express",
            "code": "express",
            "base_cost": "25.00",
            "is_default": True,
        },
    )
    assert create.status_code == 201

    store_headers = tenant_headers(tenant.slug)
    listed_public = client.get("/api/v1/shipping/methods", headers=store_headers)
    assert listed_public.status_code == 200

    calc = client.post(
        "/api/v1/shipping/calculate",
        headers=store_headers,
        json={
            "method_code": "express",
            "subtotal": "40.00",
            "shipping_address": {"city": "Nablus"},
        },
    )
    assert calc.status_code == 200
    assert calc.get_json()["shipping_cost"] == "25.00"


def test_voucher_api_create_validate_apply(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="API Voucher", slug="api-voucher", email="av@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@av.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    create = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={
            "code": "WELCOME",
            "name": "Welcome",
            "type": "percentage",
            "value": "15",
        },
    )
    assert create.status_code == 201

    store_headers = tenant_headers(tenant.slug)
    validate = client.get(
        "/api/v1/vouchers/WELCOME/validate?subtotal=100",
        headers=store_headers,
    )
    assert validate.status_code == 200

    apply_res = client.post(
        "/api/v1/vouchers/WELCOME/apply",
        headers=store_headers,
        json={"subtotal": "100"},
    )
    assert apply_res.status_code == 200
    assert apply_res.get_json()["applied"]["discount_amount"] == "15.00"

    listed = client.get("/api/v1/vouchers/", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["vouchers"]
