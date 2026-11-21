"""Store currency must reach providers and financial events (not hard-coded ILS)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from integrations.payments import stripe_connect


def test_charge_adapters_forward_currency_to_provider():
    """The charge payload uses the requested currency, never hard-coded ILS."""
    calls: list[dict] = []

    def fake_form(url, *, data, headers, idempotency):
        calls.append(data)
        return {"success": True, "data": {"id": "ch_1"}}

    fake_gateway = type("G", (), {
        "is_sandbox": False,
        "credentials_encrypted": "encrypted",
        "config": {},
    })()
    with patch.object(stripe_connect, "load_credentials", return_value={"secret_key": "sk_test"}), \
         patch.object(stripe_connect, "credentials_present", return_value=True), \
         patch.object(stripe_connect, "live_calls_enabled", return_value=True), \
         patch.object(stripe_connect, "post_form", fake_form):
        stripe_connect.charge_stripe(
            order=type("O", (), {"id": 1})(),
            gateway=fake_gateway,
            amount=Decimal("10.00"),
            currency="USD",
        )
    assert calls[0]["currency"] == "USD"


def test_payment_and_refund_currency_follows_store(app, monkeypatch):
    from catalog_svc.product_service import ProductService
    from order_svc.cart_service import CartService
    from order_svc.checkout_service import CheckoutService
    from payment_svc.payment_service import PaymentService
    from platform_svc.platform_settings_service import PlatformSettingsService
    from tenant_gateway_svc.gateway_service import GatewayService
    from tenant_svc.tenant_service import TenantService

    with app.app_context():
        PlatformSettingsService().ensure_seeded()
        tenant = TenantService().create_tenant(
            name="USD Store", slug="usd-store", email="usd@test.com"
        )
        tenant.default_currency = "USD"
        product = ProductService().create(
            tenant_id=tenant.id, name="USD Item", slug="usd-item",
            price="10.00", quantity=5, is_published=True,
        )
        cart = CartService().get_or_create_cart(tenant_id=tenant.id)
        CartService().add_item(cart=cart, product_id=product.id, quantity=1)
        order = CheckoutService().checkout(
            cart=cart, customer_email="buyer@test.com",
            shipping_address={"city": "Ramallah"},
        )
        GatewayService().ensure_cod_gateway(tenant.id)
        sent: dict = {}
        monkeypatch.setattr(
            PaymentService,
            "_charge_external_gateway",
            lambda self, order, gateway, payment: (
                sent.setdefault("currency", payment.currency),
                {"success": True, "provider_payment_id": "x"},
            )[1],
        )
        PaymentService().pay_order(
            tenant_id=tenant.id, order_public_id=str(order.public_id),
            payment_method="cod",
        )
        assert sent["currency"] == "USD"
