"""Product service unit tests (wave 2)."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError, ValidationError
from tenant_svc.tenant_service import TenantService


def test_duplicate_slug_rejected(app):
    tenants = TenantService()
    products = ProductService()
    tenant = tenants.create_tenant(
        name="Dup", slug="dup-store", email="dup@test.com"
    )
    products.create(
        tenant_id=tenant.id, name="One", slug="same-slug", price="1.00"
    )
    with pytest.raises(ValidationError):
        products.create(
            tenant_id=tenant.id, name="Two", slug="same-slug", price="2.00"
        )


def test_get_by_public_id_not_found(app):
    tenants = TenantService()
    products = ProductService()
    tenant = tenants.create_tenant(
        name="Missing", slug="missing-store", email="m@test.com"
    )
    with pytest.raises(NotFoundError):
        products.get_by_public_id(
            tenant.id, "00000000-0000-0000-0000-000000000099"
        )
