"""Tenant business logic."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from base.types import TenantStatus
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db
from tenant.tenant import Tenant
from tenant.tenant_config import TenantConfig


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
    ) -> Tenant:
        if Tenant.query.filter_by(slug=slug).first():
            raise ValidationError("Slug already exists.")
        tenant = Tenant(
            name=name,
            slug=slug,
            email=email,
            domain=domain or slug,
            status=TenantStatus.TRIAL.value,
        )
        tenant.config = TenantConfig(business_name=name)
        db.session.add(tenant)
        db.session.commit()

        from integrations.external_registry import register_tenant_subdomain

        register_tenant_subdomain(slug=tenant.slug, tenant_id=tenant.id)
        return tenant

    def list_users_for_tenant(self, tenant_id: int):
        from user.user import User

        return User.query.filter_by(tenant_id=tenant_id, deleted_at=None).all()
