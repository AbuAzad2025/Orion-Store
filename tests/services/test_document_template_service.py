"""Document template service tests (wave 5)."""

from __future__ import annotations

from platform_svc.document_template_service import DocumentTemplateService
from tenant_svc.tenant_service import TenantService


def test_document_template_upsert(app):
    tenant = TenantService().create_tenant(
        name="Doc", slug="doc-store", email="doc@test.com"
    )
    svc = DocumentTemplateService()
    row = svc.upsert(
        tenant_id=tenant.id,
        document_type="invoice",
        body_html="<p>Test</p>",
    )
    assert row.id is not None
    rows = svc.list_for_tenant(tenant.id)
    assert len(rows) == 1
    updated = svc.upsert(
        tenant_id=tenant.id,
        document_type="invoice",
        body_html="<p>Updated</p>",
    )
    assert updated.body_html == "<p>Updated</p>"
