"""Tenant-configurable non-crypto payment methods."""

from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from core.exceptions import ValidationError
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    tenant = TenantService().create_tenant(
        name="Methods Store", slug="methods-store", email="methods@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@methods.com",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def test_available_methods_exclude_crypto(app, store):
    tenant, _ = store
    with app.app_context():
        methods = GatewayService().available_methods(tenant.id, "en")
    codes = {m["code"] for m in methods}
    assert "cod" in codes and "bank_transfer" in codes and "manual" in codes
    assert not any(
        marker in code
        for code in codes
        for marker in ("crypto", "btc", "usdt", "binance", "coinbase", "wallet")
    )


def test_upsert_method_with_instructions(app, store):
    tenant, _ = store
    with app.app_context():
        svc = GatewayService()
        gateway = svc.upsert_method(
            tenant_id=tenant.id,
            code="bank_transfer",
            display_name="حوالة بنكية",
            instructions="حوّل إلى IBAN ... ثم أرسل الإيصال",
            is_enabled=True,
        )
        assert gateway.is_enabled is True
        assert gateway.config["instructions"].startswith("حوّل")
        methods = {m["code"]: m for m in svc.available_methods(tenant.id, "ar")}
        assert methods["bank_transfer"]["is_enabled"] is True
        assert methods["bank_transfer"]["instructions"].startswith("حوّل")
        checkout = svc.list_enabled_for_checkout(tenant.id)
        assert any(c["code"] == "bank_transfer" for c in checkout)


def test_crypto_provider_rejected(app, store):
    tenant, _ = store
    with app.app_context():
        svc = GatewayService()
        for code in ("usdt", "binance", "crypto", "btc_wallet"):
            with pytest.raises(ValidationError):
                svc.upsert_method(tenant_id=tenant.id, code=code)


def test_payment_methods_api(client, app, store):
    tenant, admin = store
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    listed = client.get("/api/v1/tenant/payment-methods", headers=headers)
    assert listed.status_code == 200
    assert any(m["code"] == "bank_transfer" for m in listed.get_json()["methods"])

    saved = client.post(
        "/api/v1/tenant/payment-methods",
        headers=headers,
        json={
            "code": "manual",
            "display_name": "دفع يدوي",
            "instructions": "ادفع في المتجر",
            "is_enabled": True,
        },
    )
    assert saved.status_code == 200

    rejected = client.post(
        "/api/v1/tenant/payment-methods",
        headers=headers,
        json={"code": "usdt", "is_enabled": True},
    )
    assert rejected.status_code == 400


def test_method_input_validation(app, store):
    tenant, _ = store
    with app.app_context():
        svc = GatewayService()
        bad_inputs = [
            {"display_name": 123},
            {"instructions": {"nested": "object"}},
            {"display_name": "x" * 101},
            {"instructions": "y" * 2001},
            {"is_enabled": "false"},
            {"is_enabled": 1},
        ]
        for extra in bad_inputs:
            with pytest.raises(ValidationError):
                svc.upsert_method(tenant_id=tenant.id, code="manual", **extra)


def test_available_methods_include_tenant_config(app, store):
    tenant, _ = store
    with app.app_context():
        svc = GatewayService()
        svc.upsert_method(
            tenant_id=tenant.id,
            code="bank_transfer",
            display_name="Bank",
            instructions="Pay to IBAN",
            is_enabled=True,
        )
        english = {m["code"]: m for m in svc.available_methods(tenant.id, "en")}
        assert english["bank_transfer"]["label"] == "Bank transfer"
        assert english["bank_transfer"]["instructions"] == "Pay to IBAN"
        checkout = {c["code"]: c for c in svc.list_enabled_for_checkout(tenant.id)}
        assert checkout["bank_transfer"]["instructions"] == "Pay to IBAN"


def test_gateway_service_helpers(app, store):
    from core.exceptions import NotFoundError
    from platform_models.tenant_gateway import TenantPaymentGateway

    tenant, _ = store
    with app.app_context():
        svc = GatewayService()
        with pytest.raises(NotFoundError):
            svc.get_enabled(tenant.id, "paypal")
        cod = svc.ensure_cod_gateway(tenant.id)
        assert cod.is_enabled is True
        assert svc.ensure_cod_gateway(tenant.id).id == cod.id
        assert svc.get_enabled(tenant.id, "cod").id == cod.id
        with pytest.raises(ValidationError):
            svc.upsert_paypal(tenant_id=tenant.id, client_id="", client_secret="")
        paypal = svc.upsert_paypal(
            tenant_id=tenant.id,
            client_id="client",
            client_secret="secret",
            webhook_secret="whsec",
            is_sandbox=False,
        )
        assert paypal.provider == "paypal"
        assert TenantPaymentGateway.query.filter_by(tenant_id=tenant.id).count() == 2
