"""Invoice object storage + tenant currency propagation.

Covers:
* ``InvoiceStorage``/``LocalInvoiceStorage`` put/get (incl. env override),
* invoice PDF download endpoint (owner/admin vs. everyone else),
* ``resolve_currency_for_tenant`` (custom currency + ILS default),
* currency reaching payment, financial event and invoice.
"""

from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from currency_svc.currency_service import resolve_currency_for_tenant
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.pdf_service import LocalInvoiceStorage, set_invoice_storage
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


@pytest.fixture(autouse=True)
def isolated_invoice_storage(tmp_path):
    """Keep generated PDFs out of the repo and restore the default backend."""
    storage = LocalInvoiceStorage(tmp_path / "invoices")
    set_invoice_storage(storage)
    yield storage
    set_invoice_storage(None)


def _make_store(*, slug: str, currency: str = "ILS"):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name=f"Store {slug}", slug=slug, email=f"{slug}@test.com"
    )
    tenant.default_currency = currency
    from orion.extensions import db

    db.session.commit()
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Invoice Product",
        slug=f"{slug}-product",
        price="10.00",
        quantity=10,
        is_published=True,
    )
    return tenant, product


def _pay_for_order(tenant, product, *, user_id=None, email="buyer@test.com"):
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email=email,
        user_id=user_id,
        is_guest=user_id is None,
        shipping_address={"city": "Hebron"},
    )
    return PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )


# ---------------------------------------------------------------------------
# 1. Storage put/get
# ---------------------------------------------------------------------------


def test_local_storage_put_get_roundtrip(tmp_path):
    storage = LocalInvoiceStorage(tmp_path / "objects")
    data = b"%PDF-1.7 invoice bytes"

    key = storage.put("42/INV-42-ABC12345.pdf", data)

    assert key == "42/INV-42-ABC12345.pdf"
    assert storage.get(key) == data
    assert (tmp_path / "objects" / "42" / "INV-42-ABC12345.pdf").read_bytes() == data

    with pytest.raises(KeyError):
        storage.get("42/missing.pdf")
    with pytest.raises(ValueError):
        storage.get("../outside.pdf")


def test_local_storage_honours_invoice_storage_dir_env(monkeypatch, tmp_path):
    custom = tmp_path / "custom-bucket"
    monkeypatch.setenv("INVOICE_STORAGE_DIR", str(custom))

    storage = LocalInvoiceStorage()
    assert storage.root == custom.resolve()
    assert storage.put("tenant/one.pdf", b"blob") == "tenant/one.pdf"
    assert storage.get("tenant/one.pdf") == b"blob"
    assert (custom / "tenant" / "one.pdf").read_bytes() == b"blob"


# ---------------------------------------------------------------------------
# 2. Tenant currency resolution
# ---------------------------------------------------------------------------


def test_resolve_currency_for_tenant_defaults_to_ils(app):
    from orion.extensions import db

    tenant = TenantService().create_tenant(
        name="Currency Store", slug="currency-store", email="currency@test.com"
    )
    assert resolve_currency_for_tenant(tenant.id) == "ILS"

    tenant.default_currency = "usd"
    db.session.commit()
    assert resolve_currency_for_tenant(tenant.id) == "USD"

    assert resolve_currency_for_tenant(None) == "ILS"
    assert resolve_currency_for_tenant(999_999_999) == "ILS"


# ---------------------------------------------------------------------------
# 3. Currency reaches payment / financial event / invoice
# ---------------------------------------------------------------------------


def test_custom_tenant_currency_is_used_for_invoice_and_event(app):
    tenant, product = _make_store(slug="usd-store", currency="USD")
    result = _pay_for_order(tenant, product)

    assert result["payment"]["currency"] == "USD"
    assert result["financial_event"]["currency"] == "USD"
    assert result["invoice"]["currency"] == "USD"

    from platform_models.financial_event import FinancialEvent
    from platform_models.invoice import Invoice

    invoice = Invoice.query.filter_by(tenant_id=tenant.id).one()
    event = FinancialEvent.query.filter_by(tenant_id=tenant.id).one()
    assert invoice.currency == "USD"
    assert event.currency == "USD"
    assert invoice.storage_key and invoice.storage_key.endswith(".pdf")

    from platform_svc.pdf_service import get_invoice_storage

    pdf = get_invoice_storage().get(invoice.storage_key)
    assert pdf.startswith(b"%PDF")
    assert invoice.to_dict()["currency"] == "USD"
    assert invoice.to_dict()["storage_key"] == invoice.storage_key


def test_default_tenant_currency_stays_ils(app):
    tenant, product = _make_store(slug="ils-store")
    result = _pay_for_order(tenant, product)

    assert result["payment"]["currency"] == "ILS"
    assert result["financial_event"]["currency"] == "ILS"
    assert result["invoice"]["currency"] == "ILS"


# ---------------------------------------------------------------------------
# 4. PDF download endpoint
# ---------------------------------------------------------------------------


def _paid_invoice_setup(slug: str = "pdf-store"):
    tenant, product = _make_store(slug=slug)
    auth = AuthService()
    owner = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="owner@test.com",
        password="password123",
        is_admin=False,
    )
    other = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="other@test.com",
        password="password123",
        is_admin=False,
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@test.com",
        password="password123",
        is_admin=True,
    )
    result = _pay_for_order(tenant, product, user_id=owner.id, email=owner.email)
    url = f"/api/v1/store/orders/{result['order']['public_id']}/invoice.pdf"
    return tenant, result, url, owner, other, admin


def test_invoice_pdf_download_by_owner(client, app):
    tenant, result, url, owner, _other, _admin = _paid_invoice_setup()
    headers = auth_headers(owner, tenant_id=tenant.slug)

    response = client.get(url, headers=headers)

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert "attachment" in response.headers["Content-Disposition"]
    assert result["invoice"]["invoice_number"] in response.headers["Content-Disposition"]


def test_invoice_pdf_download_by_store_admin(client, app):
    tenant, _result, url, _owner, _other, admin = _paid_invoice_setup("admin-pdf-store")
    headers = auth_headers(admin, tenant_id=tenant.slug)

    response = client.get(url, headers=headers)

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


def test_invoice_pdf_download_denies_other_customer_and_anonymous(client, app):
    tenant, _result, url, _owner, other, _admin = _paid_invoice_setup("deny-pdf-store")

    other_response = client.get(
        url, headers=auth_headers(other, tenant_id=tenant.slug)
    )
    assert other_response.status_code == 403

    anonymous = client.get(
        url, headers={"X-Tenant-ID": tenant.slug, "Content-Type": "application/json"}
    )
    assert anonymous.status_code == 401
