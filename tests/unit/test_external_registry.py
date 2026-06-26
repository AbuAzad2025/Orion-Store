"""Unit tests for outbound integration clients — mock HTTP only."""

from __future__ import annotations

import pytest
import requests

from integrations.external_registry import register_tenant_subdomain

pytestmark = pytest.mark.unit


def test_register_skipped_without_url(mocker):
    mocker.patch.dict("os.environ", {"TENANT_REGISTRY_URL": ""}, clear=False)
    assert register_tenant_subdomain(slug="x", tenant_id=1)["status"] == "skipped"


def test_register_posts_to_registry(mocker):
    mocker.patch.dict(
        "os.environ",
        {"TENANT_REGISTRY_URL": "https://registry.test"},
        clear=False,
    )
    response = mocker.Mock()
    response.raise_for_status = mocker.Mock()
    response.json.return_value = {"status": "ok"}
    post = mocker.patch.object(requests, "post", return_value=response)

    result = register_tenant_subdomain(slug="shop", tenant_id=42)

    assert result == {"status": "ok"}
    post.assert_called_once_with(
        "https://registry.test/tenants",
        json={"slug": "shop", "tenant_id": 42},
        timeout=10,
    )
