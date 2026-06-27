"""Tenant gateway management (wave 4 #41, wave 8 #62)."""

from __future__ import annotations

from core.crypto import CryptoService
from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway

PAYPAL_PROVIDER = "paypal"


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

    def list_enabled_for_checkout(self, tenant_id: int) -> list[dict]:
        gateways = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, is_enabled=True
        ).all()
        labels = {
            "cod": "الدفع عند الاستلام",
            "stripe": "Stripe",
            "paypal": "PayPal",
            "bnpl_tabby": "Tabby — ادفع لاحقاً",
            "bnpl_tamara": "Tamara — ادفع لاحقاً",
        }
        return [
            {
                "code": gw.provider,
                "label": labels.get(gw.provider, gw.display_name),
            }
            for gw in gateways
        ]

    def upsert_paypal(
        self,
        *,
        tenant_id: int,
        client_id: str,
        client_secret: str,
        webhook_secret: str | None = None,
        is_sandbox: bool = True,
        is_enabled: bool = True,
    ) -> TenantPaymentGateway:
        if not client_id or not client_secret:
            raise ValidationError("PayPal client_id and client_secret are required.")
        crypto = CryptoService()
        payload = crypto.encrypt(f"{client_id}:{client_secret}")
        gateway = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=PAYPAL_PROVIDER
        ).first()
        if not gateway:
            gateway = TenantPaymentGateway(
                tenant_id=tenant_id,
                provider=PAYPAL_PROVIDER,
                display_name="PayPal",
            )
            db.session.add(gateway)
        gateway.credentials_encrypted = payload
        if webhook_secret:
            gateway.webhook_secret = webhook_secret
        gateway.is_enabled = is_enabled
        gateway.is_sandbox = is_sandbox
        gateway.status = "active"
        gateway.connected_at = utc_now()
        db.session.commit()
        return gateway
