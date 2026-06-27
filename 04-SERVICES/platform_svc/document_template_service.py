"""Tenant document template CRUD (wave 5 #53)."""

from __future__ import annotations

from orion.extensions import db
from platform_models.invoice import TenantDocumentTemplate


class DocumentTemplateService:
    def list_for_tenant(self, tenant_id: int) -> list[TenantDocumentTemplate]:
        return (
            TenantDocumentTemplate.query.filter_by(tenant_id=tenant_id)
            .order_by(TenantDocumentTemplate.document_type)
            .all()
        )

    def upsert(
        self,
        *,
        tenant_id: int,
        document_type: str,
        locale: str = "ar",
        body_html: str | None = None,
        is_active: bool = True,
    ) -> TenantDocumentTemplate:
        row = TenantDocumentTemplate.query.filter_by(
            tenant_id=tenant_id,
            document_type=document_type,
            locale=locale,
        ).first()
        if row:
            row.body_html = body_html
            row.is_active = is_active
        else:
            row = TenantDocumentTemplate(
                tenant_id=tenant_id,
                document_type=document_type,
                locale=locale,
                body_html=body_html,
                is_active=is_active,
            )
            db.session.add(row)
        db.session.commit()
        return row
