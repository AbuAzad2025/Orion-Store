"""BNPL provider management and transactions (wave 8 #62)."""

from __future__ import annotations

from decimal import Decimal

from bnpl.bnpl_provider import BnplProvider
from bnpl.bnpl_transaction import BnplTransaction

from core.crypto import CryptoService
from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway

BNPL_PROVIDERS = ("tabby", "tamara")
BNPL_GATEWAY_PREFIX = "bnpl_"


class BnplService:
    def list_providers(self, tenant_id: int) -> list[BnplProvider]:
        rows = BnplProvider.query.filter_by(tenant_id=tenant_id).all()
        existing = {row.provider for row in rows}
        for code in BNPL_PROVIDERS:
            if code not in existing:
                rows.append(
                    BnplProvider(
                        tenant_id=tenant_id,
                        provider=code,
                        is_enabled=False,
                        config={"is_sandbox": True},
                    )
                )
        return sorted(rows, key=lambda r: r.provider)

    def get_enabled(self, tenant_id: int, provider: str) -> BnplProvider:
        if provider not in BNPL_PROVIDERS:
            raise ValidationError(f"Unsupported BNPL provider: {provider}")
        row = BnplProvider.query.filter_by(
            tenant_id=tenant_id, provider=provider, is_enabled=True
        ).first()
        if not row:
            raise NotFoundError(f"BNPL provider {provider} not enabled.")
        return row

    def upsert_provider(
        self,
        *,
        tenant_id: int,
        provider: str,
        merchant_id: str | None = None,
        api_key: str | None = None,
        is_enabled: bool = True,
        is_sandbox: bool = True,
        config: dict | None = None,
    ) -> BnplProvider:
        if provider not in BNPL_PROVIDERS:
            raise ValidationError(f"Unsupported BNPL provider: {provider}")
        row = BnplProvider.query.filter_by(
            tenant_id=tenant_id, provider=provider
        ).first()
        if not row:
            row = BnplProvider(tenant_id=tenant_id, provider=provider)
            db.session.add(row)
        if merchant_id is not None:
            row.merchant_id = merchant_id
        if api_key:
            row.api_credentials_encrypted = CryptoService().encrypt(api_key)
        row.is_enabled = is_enabled
        merged = dict(row.config or {})
        merged["is_sandbox"] = is_sandbox
        if config:
            merged.update(config)
        row.config = merged
        db.session.flush()
        self._sync_gateway(tenant_id, provider, row)
        db.session.commit()
        return row

    def create_transaction(
        self,
        *,
        tenant_id: int,
        order_id: int,
        provider: str,
        external_id: str,
        amount: Decimal,
        status: str = "captured",
        installment_plan: dict | None = None,
    ) -> BnplTransaction:
        txn = BnplTransaction(
            tenant_id=tenant_id,
            order_id=order_id,
            provider=provider,
            external_transaction_id=external_id,
            status=status,
            amount=amount,
            installment_plan=installment_plan,
        )
        db.session.add(txn)
        db.session.flush()
        return txn

    def _sync_gateway(self, tenant_id: int, provider: str, row: BnplProvider) -> None:
        gateway_code = f"{BNPL_GATEWAY_PREFIX}{provider}"
        gateway = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=gateway_code
        ).first()
        display = f"BNPL {provider.title()}"
        if not gateway:
            gateway = TenantPaymentGateway(
                tenant_id=tenant_id,
                provider=gateway_code,
                display_name=display,
            )
            db.session.add(gateway)
        gateway.display_name = display
        gateway.is_enabled = row.is_enabled
        gateway.is_sandbox = bool((row.config or {}).get("is_sandbox", True))
        gateway.status = "active" if row.is_enabled else "disconnected"
        gateway.connected_at = utc_now() if row.is_enabled else gateway.connected_at
