"""Commission service tests (wave 4)."""

from __future__ import annotations

from decimal import Decimal

from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.commission_service import CommissionService
from platform_svc.financial_events_service import FinancialEventsService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_commission_apply_from_event(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Comm", slug="comm-store", email="comm@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Commodity",
        slug="commodity",
        price="50.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="comm@test.com",
        shipping_address={"city": "Ramallah"},
    )
    event = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="50.00",
        event_type="order.payment",
        source_entity="order",
        source_id=order.id,
    )
    ledger = CommissionService().apply_from_event(event, order_id=order.id)
    assert ledger is not None
    assert ledger.commission_amount == Decimal("0.50")
    assert event.commission_ledger_id == ledger.id
