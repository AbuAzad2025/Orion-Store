"""Tenant gateway management (wave 4 #41, wave 8 #62)."""

from __future__ import annotations

from core.crypto import CryptoService
from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway

PAYPAL_PROVIDER = "paypal"

# Payment methods a tenant may offer. Crypto is intentionally absent — this
# platform is a storefront, not a digital-asset processor.
PAYMENT_METHODS: tuple[dict, ...] = (
    {
        "code": "cod",
        "ar": "الدفع عند الاستلام",
        "en": "Cash on delivery",
        "manual": True,
    },
    {
        "code": "bank_transfer",
        "ar": "تحويل بنكي",
        "en": "Bank transfer",
        "manual": True,
    },
    {
        "code": "card",
        "ar": "بطاقة ائتمان أو خصم",
        "en": "Credit or debit card",
        "manual": False,
    },
    {"code": "paypal", "ar": "باي بال", "en": "PayPal", "manual": False},
    {"code": "stripe", "ar": "سترايب", "en": "Stripe", "manual": False},
    {
        "code": "bnpl_tabby",
        "ar": "تابي — ادفع لاحقاً",
        "en": "Tabby — Pay later",
        "manual": False,
    },
    {
        "code": "bnpl_tamara",
        "ar": "تمارا — ادفع لاحقاً",
        "en": "Tamara — Pay later",
        "manual": False,
    },
    {
        "code": "manual",
        "ar": "دفع يدوي بتعليمات خاصة",
        "en": "Manual payment",
        "manual": True,
    },
)
ALLOWED_METHODS = frozenset(m["code"] for m in PAYMENT_METHODS)
CRYPTO_MARKERS = (
    "crypto",
    "btc",
    "usdt",
    "usdc",
    "binance",
    "coinbase",
    "wallet",
    "eth",
)


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
        from core.i18n_messages import localize

        labels = {
            m["code"]: localize(m["ar"], m["en"])
            for m in PAYMENT_METHODS
            if m["code"] not in ("paypal", "stripe")
        }
        labels["paypal"] = "PayPal"
        labels["stripe"] = "Stripe"
        return [
            {
                "code": gw.provider,
                "label": labels.get(gw.provider, gw.display_name),
                "instructions": (gw.config or {}).get("instructions", ""),
            }
            for gw in gateways
        ]

    def available_methods(self, tenant_id: int, locale: str = "ar") -> list[dict]:
        """All non-crypto payment methods with this tenant's current settings."""
        from core.i18n_messages import localize

        rows = {gw.provider: gw for gw in self.list_for_tenant(tenant_id)}
        result = []
        for method in PAYMENT_METHODS:
            code = method["code"]
            row = rows.get(code)
            result.append(
                {
                    "code": code,
                    "label": localize(method["ar"], method["en"], locale),
                    "display_name": row.display_name if row else "",
                    "is_enabled": bool(row and row.is_enabled),
                    "instructions": (
                        (row.config or {}).get("instructions", "") if row else ""
                    ),
                    "needs_credentials": not method["manual"],
                }
            )
        return result

    def upsert_method(
        self,
        *,
        tenant_id: int,
        code: str,
        display_name: str = "",
        instructions: str = "",
        is_enabled: bool = True,
    ) -> TenantPaymentGateway:
        """Enable/configure one non-crypto payment method for a tenant."""
        normalized = (code or "").strip().lower()
        if normalized not in ALLOWED_METHODS or any(
            marker in normalized for marker in CRYPTO_MARKERS
        ):
            raise ValidationError("Unsupported payment method.")

        if display_name is not None and not isinstance(display_name, str):
            raise ValidationError("Display name must be text.")
        if instructions is not None and not isinstance(instructions, str):
            raise ValidationError("Instructions must be text.")
        if len(display_name or "") > 100:
            raise ValidationError("Display name is too long.")
        if len(instructions or "") > 2000:
            raise ValidationError("Instructions are too long.")
        if not isinstance(is_enabled, bool):
            raise ValidationError("Invalid enabled state.")

        default = next(m for m in PAYMENT_METHODS if m["code"] == normalized)
        gateway = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=normalized
        ).first()
        if gateway is None:
            gateway = TenantPaymentGateway(
                tenant_id=tenant_id,
                provider=normalized,
                display_name=default["ar"],
                is_sandbox=True,
            )
            db.session.add(gateway)
        gateway.display_name = (display_name or "").strip() or default["ar"]
        gateway.config = {
            **(gateway.config or {}),
            "instructions": (instructions or "").strip(),
        }
        gateway.is_enabled = bool(is_enabled)
        gateway.status = "active" if is_enabled else "disconnected"
        db.session.commit()
        return gateway

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
        import json

        payload = crypto.encrypt(
            json.dumps({"client_id": client_id, "client_secret": client_secret})
        )
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
