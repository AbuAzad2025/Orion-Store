"""Wave 4 COD payment end-to-end test."""

from __future__ import annotations

from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_cod_payment_full_flow(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Pay Store", slug="pay-store", email="pay@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Payable",
        slug="payable",
        price="25.00",
        quantity=5,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=2)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="payer@test.com",
        shipping_address={"city": "Hebron"},
    )

    pay = client.post(
        f"/api/v1/store/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "cod"},
    )
    assert pay.status_code == 200
    body = pay.get_json()
    assert body["order"]["payment_status"] == "paid"
    assert body["payment"]["status"] == "completed"
    assert body["invoice"]["platform_footer_applied"] is True
    assert body["commission_ledger_id"] is not None
