"""Signed storefront tenant tokens resist guessing and tampering."""

from __future__ import annotations

import pytest

from core.store_token import issue, resolve
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    return TenantService().create_tenant(
        name="Token Store", slug="token-store", email="token@test.com"
    )


def test_roundtrip(app, store):
    with app.app_context():
        token = issue(store)
        assert resolve(token).id == store.id


def test_tampered_token_resolves_nothing(app, store):
    with app.app_context():
        token = issue(store)
        for bad in (
            token[:-1] + ("A" if token[-1] != "A" else "B"),
            token + "x",
            "garbage",
        ):
            assert resolve(bad) is None


def test_signed_store_url(app, client, store, monkeypatch):
    monkeypatch.setitem(app.config, "DEBUG", False)
    with app.app_context():
        token = issue(store)
        ok = client.get(f"/?store={token}")
        bad = client.get("/?store=tampered-token")
    assert ok.status_code == 200
    assert bad.status_code == 404


def test_plain_slug_rejected_in_production(app, client, store, monkeypatch):
    monkeypatch.setitem(app.config, "DEBUG", False)
    response = client.get("/?tenant_slug=token-store")
    assert response.status_code == 404
