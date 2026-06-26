"""Category service unit tests (wave 2)."""

from __future__ import annotations

import pytest

from catalog_svc.category_service import CategoryService
from core.exceptions import NotFoundError
from tenant_svc.tenant_service import TenantService


def test_create_nested_category(app):
    tenants = TenantService()
    categories = CategoryService()
    tenant = tenants.create_tenant(
        name="Nested", slug="nested-store", email="nested@test.com"
    )
    parent = categories.create(
        tenant_id=tenant.id, name="Root", slug="root", parent_id=None
    )
    child = categories.create(
        tenant_id=tenant.id,
        name="Child",
        slug="child",
        parent_id=parent.id,
    )
    assert child.level == 1
    assert child.path == "root/child"


def test_parent_not_found_raises(app):
    tenants = TenantService()
    categories = CategoryService()
    tenant = tenants.create_tenant(
        name="Orphan", slug="orphan-store", email="orphan@test.com"
    )
    with pytest.raises(NotFoundError):
        categories.create(
            tenant_id=tenant.id, name="X", slug="x", parent_id=99999
        )
