"""Document template service tests (wave 5)."""

from __future__ import annotations

from platform_svc.document_template_service import DocumentTemplateService
from tenant_svc.tenant_service import TenantService


def test_document_template_upsert(app):
    tenant = TenantService().create_tenant(
        name="Doc", slug="doc-store", email="doc@test.com"
    )
    svc = DocumentTemplateService()
    valid = (
        '<div>Test</div>'
        '<footer id="azadexa-platform-footer" data-immutable="true"></footer>'
    )
    row = svc.upsert(
        tenant_id=tenant.id,
        document_type="invoice",
        body_html=valid,
    )
    assert row.id is not None
    rows = svc.list_for_tenant(tenant.id)
    assert len(rows) == 1
    updated = svc.upsert(
        tenant_id=tenant.id,
        document_type="invoice",
        body_html=valid.replace("Test", "Updated"),
    )
    assert "Updated" in updated.body_html
