"""Tenant gateway management (wave 4 #41)."""

from __future__ import annotations

from core.exceptions import NotFoundError
from core.utils import utc_now
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway


class GatewayService:
    def get_enabled(self, tenant_id: int, provider: str) -> TenantPaymentGateway:
        gateway = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=provider, is_enabled=True
        ).first()
        if not gateway:
            raise NotFoundError(f"Gateway {provider} not enabled for tenant.")
        return gateway

    def ensure_cod_gateway(self, tenant_id: int) -> TenantPaymentGateway:
        gateway = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider="cod"
        ).first()
        if gateway:
            return gateway
        gateway = TenantPaymentGateway(
            tenant_id=tenant_id,
            provider="cod",
            display_name="Cash on Delivery",
            is_enabled=True,
            is_sandbox=False,
            status="active",
            connected_at=utc_now(),
        )
        db.session.add(gateway)
        db.session.commit()
        return gateway

    def list_for_tenant(self, tenant_id: int) -> list[TenantPaymentGateway]:
        return TenantPaymentGateway.query.filter_by(tenant_id=tenant_id).all()
