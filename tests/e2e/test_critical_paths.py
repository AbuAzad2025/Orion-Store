"""Production-critical browser paths (storefront, admin login, product management)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService

pytestmark = pytest.mark.e2e


def test_storefront_browse_cart_checkout(
    server_url: str, browser_page: Page, app, capture_shot
) -> None:
    tenant = TenantService().create_tenant(
        name="E2E Store", slug="e2e-store", email="e2e@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="E2E Product",
        slug="e2e-product",
        price="19.99",
        quantity=10,
        is_published=True,
    )

    browser_page.goto(
        f"{server_url}/?tenant_slug={tenant.slug}", wait_until="domcontentloaded"
    )
    assert browser_page.locator("body").is_visible()
    assert browser_page.get_by_text("E2E Product").count() >= 1
    capture_shot(browser_page, "storefront_index")

    browser_page.goto(
        f"{server_url}/cart?tenant_slug={tenant.slug}", wait_until="domcontentloaded"
    )
    assert "cart" in browser_page.content().lower()

    # Configure WhatsApp and prove both purchase paths stay available.
    from orion.extensions import db
    from tenant.tenant import Tenant

    product_id = product.id
    with app.app_context():
        row = db.session.get(Tenant, tenant.id)
        row.phone = "+970501234567"
        db.session.commit()

    browser_page.evaluate(
        """async (productId) => {
            const created = await StoreAPI.createCart();
            StoreAPI.setCartToken(created.cart.cart_token);
            await StoreAPI.addItem(created.cart.cart_token, productId, 1);
        }""",
        product_id,
    )
    browser_page.reload(wait_until="domcontentloaded")
    assert browser_page.locator('a[href^="/checkout"]').is_visible()
    assert browser_page.locator("#whatsapp-order-btn").is_visible()
    assert "E2E Product" in browser_page.locator("#cart-items").inner_text()
    capture_shot(browser_page, "storefront_cart")

    browser_page.goto(
        f"{server_url}/checkout?tenant_slug={tenant.slug}",
        wait_until="domcontentloaded",
    )
    assert "checkout" in browser_page.content().lower()


def test_tenant_admin_login(
    server_url: str, browser_page: Page, app, capture_shot
) -> None:
    tenant = TenantService().create_tenant(
        name="E2E Admin Store", slug="e2e-admin", email="admin-e2e@test.com"
    )
    AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin-e2e@test.com",
        password="password123",
        is_admin=True,
    )

    browser_page.goto(f"{server_url}/admin/login", wait_until="domcontentloaded")
    browser_page.fill('input[name="email"]', "admin-e2e@test.com")
    browser_page.fill('input[name="password"]', "password123")
    browser_page.fill('input[name="tenant_slug"]', tenant.slug)
    browser_page.click('button[type="submit"]')
    browser_page.wait_for_url("**/admin/store/dashboard", timeout=10000)
    assert "dashboard" in browser_page.content().lower()
    assert browser_page.locator(".orion-topbar").count() == 1
    assert browser_page.locator(".orion-skip-link").count() == 1
    assert browser_page.locator(".orion-breadcrumb").count() == 1
    capture_shot(browser_page, "tenant_dashboard")

    browser_page.goto(f"{server_url}/admin/store/ui-kit", wait_until="domcontentloaded")
    assert browser_page.locator(".orion-card").count() >= 4
    assert browser_page.locator(".orion-btn-gold").count() >= 1
    assert browser_page.locator("table.orion-table").count() == 1
    capture_shot(browser_page, "ui_kit")

    for name, path in (
        ("tenant_gateways", "/admin/store/gateways"),
        ("tenant_tax", "/admin/store/tax"),
        ("tenant_returns", "/admin/store/returns"),
    ):
        response = browser_page.goto(
            f"{server_url}{path}", wait_until="domcontentloaded"
        )
        assert response.status == 200
        assert browser_page.locator(".orion-card").count() >= 1
        capture_shot(browser_page, name)


def test_platform_admin_login(
    server_url: str, browser_page: Page, app, capture_shot
) -> None:
    AuthService().register_super_admin(
        email="owner-e2e@azadexa.com", password="password123"
    )
    browser_page.goto(f"{server_url}/admin/login", wait_until="domcontentloaded")
    browser_page.fill('input[name="email"]', "owner-e2e@azadexa.com")
    browser_page.fill('input[name="password"]', "password123")
    browser_page.click('button[type="submit"]')
    browser_page.wait_for_url("**/admin/platform/dashboard", timeout=10000)
    assert "dashboard" in browser_page.content().lower()
    assert browser_page.locator(".orion-topbar").count() == 1
    assert browser_page.locator(".orion-breadcrumb").count() == 1
    capture_shot(browser_page, "platform_dashboard")

    for name, path in (
        ("platform_tenants", "/admin/platform/tenants"),
        ("platform_users", "/admin/platform/users"),
    ):
        response = browser_page.goto(
            f"{server_url}{path}", wait_until="domcontentloaded"
        )
        assert response.status == 200
        assert browser_page.locator(".orion-card").count() >= 1
        capture_shot(browser_page, name)

    capabilities = browser_page.evaluate("""() => ({
            request: typeof OrionAPI.request === 'function',
            timeout: OrionAPI.timeoutMs > 0,
            toast: typeof OrionUI.toast === 'function',
            loading: typeof OrionUI.withLoading === 'function',
        })""")
    assert all(capabilities.values()), capabilities

    browser_page.evaluate(
        """() => document.dispatchEvent(new CustomEvent('orion-api-error', {
            detail: { error: { message: 'اختبار رسالة الخطأ' } }
        }))"""
    )
    assert browser_page.locator(".orion-toast-error").count() == 1
    browser_page.evaluate(
        "() => document.querySelectorAll('.orion-toast').forEach((el) => el.remove())"
    )


def test_tenant_admin_manages_products_from_dashboard(
    server_url: str, browser_page: Page, app, capture_shot
) -> None:
    tenant = TenantService().create_tenant(
        name="UI Catalog Store", slug="ui-catalog", email="ui-catalog@test.com"
    )
    AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="ui-catalog-admin@test.com",
        password="password123",
        is_admin=True,
    )

    browser_page.goto(f"{server_url}/admin/login", wait_until="domcontentloaded")
    browser_page.fill('input[name="email"]', "ui-catalog-admin@test.com")
    browser_page.fill('input[name="password"]', "password123")
    browser_page.fill('input[name="tenant_slug"]', tenant.slug)
    browser_page.click('button[type="submit"]')
    browser_page.wait_for_url("**/admin/store/dashboard", timeout=10000)

    browser_page.goto(
        f"{server_url}/admin/store/products", wait_until="domcontentloaded"
    )
    assert browser_page.locator("#product-form").is_visible()
    browser_page.fill("#p-name", "منتج من اللوحة")
    browser_page.fill("#p-slug", "dashboard-product")
    browser_page.fill("#p-price", "33.00")
    browser_page.fill("#p-image", "https://example.com/dashboard.jpg")
    browser_page.locator("#p-published").check()
    browser_page.locator("#product-form button[type=submit]").click()
    browser_page.get_by_text("منتج من اللوحة").first.wait_for(timeout=10000)
    capture_shot(browser_page, "product_management")

    browser_page.goto(
        f"{server_url}/?tenant_slug={tenant.slug}", wait_until="domcontentloaded"
    )
    assert browser_page.locator('img[alt="منتج من اللوحة"]').count() == 1
