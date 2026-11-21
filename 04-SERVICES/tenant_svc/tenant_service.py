"""Tenant business logic."""

from __future__ import annotations

import logging

from sqlalchemy.orm import joinedload

from base.types import TenantStatus
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db
from tenant.tenant import Tenant
from tenant.tenant_config import TenantConfig

logger = logging.getLogger(__name__)


class TenantService:
    def list_tenants(self) -> list[Tenant]:
        return (
            Tenant.query.options(joinedload(Tenant.config))
            .filter(Tenant.deleted_at.is_(None))
            .order_by(Tenant.created_at.desc())
            .all()
        )

    def get_by_public_id(self, public_id: str) -> Tenant:
        tenant = (
            Tenant.query.options(joinedload(Tenant.config))
            .filter_by(public_id=public_id, deleted_at=None)
            .first()
        )
        if not tenant:
            raise NotFoundError("Tenant not found.")
        return tenant

    def create_tenant(
        self,
        *,
        name: str,
        slug: str,
        email: str,
        domain: str | None = None,
        status: str | None = None,
    ) -> Tenant:
        if status is not None:
            allowed = {s.value for s in TenantStatus}
            if status not in allowed:
                raise ValidationError("Invalid tenant status.")
        if Tenant.query.filter_by(slug=slug).first():
            raise ValidationError("Slug already exists.")
        tenant = Tenant(
            name=name,
            slug=slug,
            email=email,
            domain=domain or slug,
            status=status or TenantStatus.TRIAL.value,
        )
        tenant.config = TenantConfig(business_name=name)
        db.session.add(tenant)
        db.session.commit()

        from core.audit_log import audit_log

        audit_log(
            action="tenant.created",
            resource_type="tenant",
            resource_id=str(tenant.id),
            tenant_id=tenant.id,
            details={"slug": tenant.slug, "name": tenant.name},
        )

        from integrations.external_registry import register_tenant_subdomain

        # DNS/routing registration is best-effort: a failed external call must
        # not roll back an already-persisted (and audited) tenant or surface as
        # a 5xx that would make the caller retry and create a duplicate.
        try:
            register_tenant_subdomain(slug=tenant.slug, tenant_id=tenant.id)
        except Exception as exc:
            logger.warning(
                "Subdomain registration failed for tenant %s (%s): %s",
                tenant.slug,
                tenant.id,
                exc,
            )
        return tenant

    def list_users_for_tenant(self, tenant_id: int):
        from user.user import User

        return User.query.filter_by(tenant_id=tenant_id, deleted_at=None).all()
