"""Closed-beta gate tests."""

from __future__ import annotations

import pytest

from core.beta_gate import (
    beta_allowlist,
    enforce_beta_tenant_access,
    is_beta_gated_path,
    is_tenant_beta_allowed,
)
from core.exceptions import AuthorizationError
from support.http import tenant_headers

from tenant_svc.tenant_service import TenantService


def test_beta_disabled_allows_all(app):
    with app.app_context():
        assert is_tenant_beta_allowed("any-store") is True


def test_beta_allowlist_enforced(app):
    app.config["TESTING"] = False
    app.config["BETA_MODE"] = True
    app.config["BETA_TENANT_SLUGS"] = "beta-ramallah,beta-amman"
    with app.app_context():
        assert is_tenant_beta_allowed("beta-ramallah") is True
        assert is_tenant_beta_allowed("other-store") is False
        assert beta_allowlist() == {"beta-ramallah", "beta-amman"}


def test_enforce_beta_raises_for_blocked_slug(app):
    app.config["TESTING"] = False
    app.config["BETA_MODE"] = True
    app.config["BETA_TENANT_SLUGS"] = "beta-amman"
    with app.app_context():
        with pytest.raises(AuthorizationError):
            enforce_beta_tenant_access("blocked-store")


def test_is_beta_gated_path():
    assert is_beta_gated_path("/api/v1/store/products") is True
    assert is_beta_gated_path("/health") is False
    assert is_beta_gated_path("/") is True
    assert is_beta_gated_path("/api/v1/platform/status") is False


def test_storefront_blocked_outside_beta(client, app):
    app.config["TESTING"] = False
    app.config["BETA_MODE"] = True
    app.config["BETA_TENANT_SLUGS"] = "allowed-only"
    tenant = TenantService().create_tenant(
        name="Blocked", slug="blocked-beta", email="blocked@beta.com"
    )
    headers = tenant_headers(tenant.slug)
    resp = client.get("/api/v1/store/products", headers=headers)
    assert resp.status_code == 403
