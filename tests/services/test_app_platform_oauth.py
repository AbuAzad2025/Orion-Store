"""Real app-platform OAuth flow + webhook dispatcher (no mocked CRUD).

Covers the user-visible behaviour:
  * registration returns a real raw client_secret exactly once (stored salted);
  * /oauth/token and /oauth/authorize issue a signed JWT with scope + app_id;
  * a wrong secret is rejected;
  * installation records the authenticated user, never a client-supplied 0;
  * the app webhook dispatcher verifies the subscription HMAC and acknowledges.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from app_platform.app_platform import AppInstallation, OAuthApplication
from flask_jwt_extended import decode_token
from support.http import auth_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

BASE = "/api/v1/app-platform"
SCOPES = "read_products write_products"


@pytest.fixture
def oauth_setup(app):
    PlatformSettingsService().ensure_seeded()
    suffix = uuid.uuid4().hex[:10]
    tenant = TenantService().create_tenant(
        name="OAuth Platform",
        slug=f"oauth-{suffix}",
        email=f"oauth-{suffix}@test.com",
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email=f"admin-{suffix}@test.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    return {"tenant": tenant, "admin_id": admin.id, "headers": headers}


def _register(client, headers):
    resp = client.post(
        f"{BASE}/apps",
        headers=headers,
        json={
            "name": "Integration App",
            "redirect_uris": ["https://app.example/callback"],
            "scopes": SCOPES,
        },
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _install(client, headers, app_id):
    resp = client.post(
        f"{BASE}/apps/{app_id}/install",
        headers=headers,
        # Deliberately lie about installed_by — the API must ignore it.
        json={"installed_by": 999999},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["installation"]


def _token_request(
    client, client_id, secret, *, endpoint="oauth/token", scope="read_products"
):
    return client.post(
        f"{BASE}/{endpoint}",
        json={
            "client_id": client_id,
            "client_secret": secret,
            "scope": scope,
            "grant_type": "client_credentials",
        },
    )


def test_register_returns_raw_secret_once(client, app, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    raw = data["client_secret"]
    assert raw and len(raw) >= 32
    assert data["app"]["client_secret"] == raw

    with app.app_context():
        record = OAuthApplication.query.filter_by(
            client_id=data["app"]["client_id"]
        ).one()
        stored = record.client_secret_hash
        assert "$" in stored
        assert stored != raw
        assert raw not in stored

    # Subsequent reads never expose the secret again.
    listing = client.get(f"{BASE}/apps", headers=oauth_setup["headers"])
    assert listing.status_code == 200
    assert all("client_secret" not in a for a in listing.get_json()["apps"])


@pytest.mark.parametrize("endpoint", ["oauth/token", "oauth/authorize"])
def test_valid_raw_secret_issues_signed_token(client, app, oauth_setup, endpoint):
    data = _register(client, oauth_setup["headers"])
    resp = _token_request(
        client,
        data["app"]["client_id"],
        data["client_secret"],
        endpoint=endpoint,
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["token_type"] == "Bearer"
    assert body["scope"] == "read_products"
    assert body["app_id"] == data["app"]["id"]

    with app.app_context():
        claims = decode_token(body["access_token"])
    assert claims["sub"] == data["app"]["client_id"]
    assert claims["scope"] == "read_products"
    assert claims["app_id"] == data["app"]["id"]
    assert claims["tenant_id"] == oauth_setup["tenant"].id


def test_wrong_secret_is_rejected(client, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    resp = _token_request(client, data["app"]["client_id"], "definitely-wrong-secret")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_unsupported_scope_is_rejected(client, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    resp = _token_request(
        client,
        data["app"]["client_id"],
        data["client_secret"],
        scope="delete_everything",
    )
    assert resp.status_code == 400


def test_install_uses_current_authenticated_user(client, app, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    inst_id = _install(client, oauth_setup["headers"], data["app"]["id"])["id"]

    with app.app_context():
        inst = AppInstallation.query.filter_by(id=inst_id).one()
        assert inst.installed_by == oauth_setup["admin_id"]
        assert inst.installed_by != 0


def _app_webhook(client, tenant_id, event_type, payload, signature):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Webhook-Signature"] = signature
    return client.post(
        f"/webhooks/app/{tenant_id}/{event_type}",
        data=raw,
        headers=headers,
    )


def test_signed_app_webhook_is_acknowledged(client, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    inst = _install(client, oauth_setup["headers"], data["app"]["id"])

    sub_resp = client.post(
        f"{BASE}/installations/{inst['id']}/webhooks",
        headers=oauth_setup["headers"],
        json={
            "topic": "orders.created",
            "callback_url": "https://app.example/hooks",
        },
    )
    assert sub_resp.status_code == 201, sub_resp.get_json()
    secret = sub_resp.get_json()["webhook"]["webhook_secret"]
    assert secret and len(secret) >= 32

    payload = {"id": f"evt-{uuid.uuid4().hex}", "order_id": 42}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    resp = _app_webhook(
        client, oauth_setup["tenant"].id, "orders.created", payload, sig
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["received"] is True
    assert body["event_type"] == "orders.created"
    assert body["tenant_id"] == oauth_setup["tenant"].id


def test_unsigned_or_badly_signed_app_webhook_is_rejected(client, oauth_setup):
    data = _register(client, oauth_setup["headers"])
    inst = _install(client, oauth_setup["headers"], data["app"]["id"])
    sub_resp = client.post(
        f"{BASE}/installations/{inst['id']}/webhooks",
        headers=oauth_setup["headers"],
        json={"topic": "orders.created", "callback_url": "https://app.example/hooks"},
    )
    assert sub_resp.status_code == 201
    payload = {"id": f"evt-{uuid.uuid4().hex}"}

    missing = _app_webhook(
        client, oauth_setup["tenant"].id, "orders.created", payload, None
    )
    assert missing.status_code == 400

    bad = _app_webhook(
        client, oauth_setup["tenant"].id, "orders.created", payload, "bad-signature"
    )
    assert bad.status_code == 400
