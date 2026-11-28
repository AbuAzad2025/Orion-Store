"""Integration coverage push for remaining v1 API error/edge branches.

All requests go through the Flask test client and real PostgreSQL-backed
services. Only HTTP payloads, headers and signed webhook bodies vary.
"""

# fmt: off  # compact data tables keep this file inside the 500-line repository gate

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from affiliate_svc.affiliate_service import AffiliateService
from app_platform_svc.app_platform_service import AppPlatformService
from bopis_svc.bopis_service import BopisService
from compliance_svc.compliance_service import ComplianceService
from gift_svc.gift_registry_service import GiftRegistryService
from i18n_svc.page_service import PageService
from shipping_svc.shipping_service import ShippingService
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from order.order import Order
from orion.extensions import db
from platform_models.invoice import Invoice
from platform_svc.platform_settings_service import PlatformSettingsService
from rma_svc.rma_service import RmaService
from tenant_svc.tenant_service import TenantService

SECRET = "whsec_push_api_test"


class _ClaimCache:
    """In-process replay-guard cache (infrastructure, not core CRUD)."""

    available = True

    def __init__(self):
        self.seen = set()

    def set_nx(self, key, value):
        if key in self.seen:
            return False
        self.seen.add(key)
        return True


@pytest.fixture
def claim_cache(app):
    original = app.extensions.get("redis_cache")
    app.extensions["redis_cache"] = _ClaimCache()
    yield
    app.extensions["redis_cache"] = original


def _req(c, method, path, headers=None, payload=None):
    kw = {}
    if headers is not None:
        kw["headers"] = headers
    if payload is not None:
        kw["json"] = payload
    return getattr(c, method)(path, **kw)


def _bad(c, method, path, headers=None, payload=None):
    r = _req(c, method, path, headers, payload)
    assert r.status_code in (400, 401, 403, 404, 405), (path, r.status_code)


@pytest.fixture
def env(app):
    with app.app_context():
        PlatformSettingsService().ensure_seeded()
        s = uuid.uuid4().hex[:8]
        t = TenantService().create_tenant(
            name="Push API", slug=f"push-{s}", email=f"push-{s}@test.com"
        )
        t.phone = "+970501234567"
        admin = AuthService().register_tenant_user(
            tenant_id=t.id,
            email=f"admin-{s}@test.com",
            password="password123",
            is_admin=True,
        )
        buyer = AuthService().register_tenant_user(
            tenant_id=t.id,
            email=f"buyer-{s}@test.com",
            password="password123",
            is_admin=False,
        )
        other = AuthService().register_tenant_user(
            tenant_id=t.id,
            email=f"other-{s}@test.com",
            password="password123",
            is_admin=False,
        )
        product = ProductService().create(
            tenant_id=t.id,
            name="Push Product",
            slug=f"push-p-{s}",
            price="25.00",
            quantity=20,
            is_published=True,
        )
        category = CategoryService().create(
            tenant_id=t.id, name="Push Category", slug=f"push-c-{s}"
        )
        method = ShippingService().create_method(
            tenant_id=t.id, name="Push Shipping", code=f"push-{s}", base_cost="5.00"
        )
        db.session.commit()
        return SimpleNamespace(
            tid=t.id,
            admin_id=admin.id,
            buyer_id=buyer.id,
            buyer_email=buyer.email,
            other_email=other.email,
            buyer_pid=buyer.public_id,
            pid=product.id,
            pslug=product.slug,
            ppid=product.public_id,
            cid=category.id,
            cslug=category.slug,
            ah=auth_headers(admin, app=app, tenant_id=t.slug),
            bh=auth_headers(buyer, app=app, tenant_id=t.slug),
            oh=auth_headers(other, app=app, tenant_id=t.slug),
            sh=tenant_headers(t.slug),
        )


def _order(env, app, user_id=None, email=None):
    with app.app_context():
        o = Order(
            tenant_id=env.tid,
            user_id=user_id,
            order_number=f"PUSH-{uuid.uuid4().hex[:10]}",
            customer_email=email or env.buyer_email,
            shipping_address={},
            subtotal="10.00",
            tax_amount="0",
            shipping_cost="0",
            discount_amount="0",
            total="10.00",
            status="pending",
            payment_status="pending",
            is_guest=user_id is None,
        )
        db.session.add(o)
        db.session.commit()
        return str(o.public_id), o.id


# storefront.py / store_whatsapp.py / storefront_pickup.py / order_access.py
def test_storefront_context_errors(client, env):
    for method, path in (
        ("get", "/api/v1/store/products"),
        ("get", "/api/v1/store/categories"),
        ("get", "/api/v1/store/categories/missing"),
        ("get", "/api/v1/store/products/missing"),
        ("post", "/api/v1/store/cart"),
        ("get", "/api/v1/store/cart/bad-token"),
        ("post", "/api/v1/store/cart/bad-token/items"),
        ("get", "/api/v1/store/shipping/methods"),
        ("post", "/api/v1/store/checkout"),
        ("get", "/api/v1/store/payment-methods"),
        ("post", "/api/v1/store/orders/x/pay"),
        ("get", "/api/v1/store/orders/x"),
        ("get", "/api/v1/store/orders/x/invoice"),
        ("get", "/api/v1/store/orders/x/invoice.pdf"),
        ("post", "/api/v1/store/cart/bad-token/whatsapp-message"),
        ("get", "/api/v1/store/pickup-locations"),
    ):
        _bad(client, method, path)
    h = env.sh
    assert client.get("/api/v1/store/categories", headers=h).status_code == 200
    assert (
        client.get(f"/api/v1/store/categories/{env.cslug}", headers=h).status_code
        == 200
    )
    _bad(client, "get", "/api/v1/store/categories/does-not-exist", h)
    assert (
        client.get(f"/api/v1/store/products/{env.pslug}", headers=h).status_code == 200
    )
    for path in ("/shipping/methods", "/payment-methods", "/pickup-locations"):
        assert client.get(f"/api/v1/store{path}", headers=h).status_code == 200


def test_storefront_cart_checkout_pickup(client, env, app):
    h = env.sh
    token = client.post("/api/v1/store/cart", headers=h).get_json()["cart"][
        "cart_token"
    ]
    _bad(client, "post", f"/api/v1/store/cart/{token}/items", h, {"product_id": "x"})
    _bad(client, "post", "/api/v1/store/cart/bad/items", h, {"product_id": env.pid})
    _bad(client, "post", "/api/v1/store/checkout", h, {})
    _bad(client, "post", "/api/v1/store/checkout", h, {"cart_token": "bad"})
    assert (
        client.post(
            f"/api/v1/store/cart/{token}/items", headers=h, json={"product_id": env.pid}
        ).status_code
        == 201
    )
    with app.app_context():
        loc = BopisService().create_location(
            tenant_id=env.tid,
            code=f"PU-{uuid.uuid4().hex[:6]}",
            name="Pickup",
            address={},
        )
        BopisService().create_slot(
            location_id=loc.id,
            tenant_id=env.tid,
            day_of_week=datetime.utcnow().weekday(),
            start_time="10:00",
            end_time="18:00",
        )
        loc_id = loc.id
    r = client.post(
        "/api/v1/store/checkout",
        headers=h,
        json={
            "cart_token": token,
            "customer_email": "guest@test.com",
            "pickup_location_id": loc_id,
        },
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["pickup"] is not None


def test_storefront_ownership_invoice(client, env, app, platform_admin_headers):
    pid, oid = _order(env, app, user_id=env.buyer_id)
    url = f"/api/v1/store/orders/{pid}"
    su = {**platform_admin_headers, "X-Tenant-ID": env.sh["X-Tenant-ID"]}
    for h in (env.sh, env.bh, env.ah, su):
        assert client.get(url, headers=h).status_code == 200
    _bad(client, "post", f"{url}/pay", env.oh, {})
    _bad(client, "get", f"{url}/invoice", env.sh)
    with app.app_context():
        db.session.add(
            Invoice(
                tenant_id=env.tid,
                order_id=oid,
                invoice_number=f"INV-{uuid.uuid4().hex[:10]}",
                subtotal="10.00",
                total_amount="10.00",
                rendered_html="<p>x</p>",
            )
        )
        db.session.commit()
    for h in (env.sh, env.oh, env.ah):
        _bad(client, "get", f"{url}/invoice.pdf", h)
    with app.app_context():
        inv = Invoice.query.filter_by(tenant_id=env.tid).first()
        inv.storage_key = "missing-invoice.pdf"
        db.session.commit()
    _bad(client, "get", f"{url}/invoice.pdf", env.ah)


# tenant_portal.py
def test_tenant_portal_errors(client, env):
    base = "/api/v1/tenant"
    for method, path, payload in (
        ("get", "/dashboard", None),
        ("get", "/contact", None),
        ("put", "/contact", {}),
        ("get", "/gateways", None),
        ("post", "/gateways/cod", {}),
        ("post", "/gateways/paypal", {}),
        ("get", "/bnpl/providers", None),
        ("put", "/bnpl/providers/tabby", {}),
        ("get", "/document-templates", None),
        ("put", "/document-templates/invoice", {}),
        ("post", "/payments/bad/refund", {}),
        ("get", "/feature-flags", None),
        ("put", "/feature-flags/draft_orders_enabled", {}),
        ("get", f"/products/{env.ppid}/translations", None),
        ("put", f"/products/{env.ppid}/translations/ar", {}),
        ("put", "/categories/999999/translations/ar", {}),
    ):
        _bad(client, method, f"{base}{path}", payload=payload)


def test_tenant_portal_admin_validation(client, env):
    base, h = "/api/v1/tenant", env.ah
    _bad(client, "put", f"{base}/contact", h, {"phone": "abc"})
    assert (
        client.put(
            f"{base}/feature-flags/draft_orders_enabled",
            headers=h,
            json={"value": None},
        ).status_code
        == 200
    )
    _bad(client, "put", f"{base}/feature-flags/no-such-flag", h, {"value": True})
    _bad(client, "post", f"{base}/payments/bad/refund", h, {})
    _bad(client, "get", f"{base}/products/no-such-product/translations", h)
    assert (
        client.get(f"{base}/products/{env.ppid}/translations", headers=h).status_code
        == 200
    )
    assert (
        client.put(
            f"{base}/products/{env.ppid}/translations/ar",
            headers=h,
            json={"name": "Push AR"},
        ).status_code
        == 200
    )
    _bad(client, "put", f"{base}/products/{env.ppid}/translations/ar", h, {})
    _bad(client, "put", f"{base}/categories/999999/translations/ar", h, {"name": "x"})
    assert (
        client.put(
            f"{base}/categories/{env.cid}/translations/ar",
            headers=h,
            json={"name": "تصنيف"},
        ).status_code
        == 200
    )
    _bad(client, "put", f"{base}/categories/{env.cid}/translations/ar", h, {})


# store_account.py / customer_flows.py
def test_store_account(client, env, app, platform_admin_headers):
    base = "/api/v1/store/account"
    _bad(client, "post", f"{base}/register")
    _bad(client, "post", f"{base}/register", env.sh, {})
    assert (
        client.post(
            f"{base}/login",
            headers=env.sh,
            json={"email": env.buyer_email, "password": "password123"},
        ).status_code
        == 200
    )
    for cookie in ("access_token_cookie", "refresh_token_cookie"):
        client.flask_client.delete_cookie(cookie)
    _bad(client, "post", f"{base}/login")
    _bad(client, "post", f"{base}/login", env.sh, {})
    _bad(client, "post", f"{base}/data-requests", env.bh, {"request_type": "bad"})
    _bad(
        client,
        "post",
        f"{base}/data-requests",
        platform_admin_headers,
        {"request_type": "export"},
    )
    with app.app_context():
        svc = ComplianceService()
        foreign = svc.create_data_request(
            tenant_id=env.tid, customer_email=env.other_email, request_type="export"
        )
        own = svc.create_data_request(
            tenant_id=env.tid, customer_email=env.buyer_email, request_type="export"
        )
        dele = svc.create_data_request(
            tenant_id=env.tid, customer_email=env.buyer_email, request_type="delete"
        )
        fid, oid2, did = foreign.id, own.id, dele.id
    _bad(client, "get", f"{base}/data-requests/{fid}/export", env.bh)
    _bad(client, "get", f"{base}/data-requests/999999/export", env.bh)
    assert (
        client.get(f"{base}/data-requests/{oid2}/export", headers=env.bh).status_code
        == 200
    )
    _bad(client, "post", f"{base}/data-requests/{fid}/delete", env.bh)
    _bad(client, "post", f"{base}/data-requests/{oid2}/delete", env.bh)
    _bad(client, "post", f"{base}/data-requests/999999/delete", env.bh)
    assert (
        client.post(f"{base}/data-requests/{did}/delete", headers=env.bh).status_code
        == 200
    )
    su = {**platform_admin_headers, "X-Tenant-ID": env.sh["X-Tenant-ID"]}
    _bad(client, "get", f"{base}/me", su)
    _bad(client, "get", f"{base}/orders", su)
    with app.app_context():
        fake = auth_headers("not-a-uuid", app=app, tenant_id=env.sh["X-Tenant-ID"])
    _bad(client, "get", f"{base}/me", fake)


def test_customer_flows(client, env, platform_admin_headers, app):
    base = "/api/v1/store/account"
    for method, path in (
        ("get", "/plans"),
        ("post", "/subscribe"),
        ("get", "/credit"),
        ("get", "/quote-requests"),
        ("post", "/quote-requests"),
        ("get", "/gift-registries"),
        ("post", "/gift-registries"),
        ("post", "/gift-registries/no-such/items"),
    ):
        _bad(client, method, f"{base}{path}", platform_admin_headers)
    for path, payload in (
        ("/subscribe", {}),
        ("/quote-requests", {"product_id": "x"}),
        ("/gift-registries", {}),
        ("/gift-registries/no-such/items", {}),
    ):
        _bad(client, "post", f"{base}{path}", env.ah, payload)
    with app.app_context():
        reg = GiftRegistryService().create_registry(
            tenant_id=env.tid,
            customer_email=env.buyer_email,
            registry_name="Push Registry",
            user_id=env.buyer_id,
        )
        slug = reg.slug
    _bad(
        client,
        "post",
        f"{base}/gift-registries/{slug}/items",
        env.ah,
        {"product_id": env.pid},
    )


# compliance.py / subscriptions.py / b2b.py / i18n.py / users.py
def test_compliance(client, env):
    base = "/api/v1/compliance"
    assert (
        client.post(
            f"{base}/consent/public", headers=env.sh, json={"choice": "all"}
        ).status_code
        == 201
    )
    _bad(client, "post", f"{base}/consent/public", env.sh, {"choice": "bad"})
    _bad(client, "post", f"{base}/consent/public", None, {"choice": "all"})
    for path in ("/consent", "/data-requests", "/cookie-settings", "/sso"):
        _bad(client, "get", f"{base}{path}")
    for path in ("/consent", "/data-requests", "/sso"):
        _bad(client, "post", f"{base}{path}", env.ah, {})
    for path in (
        "/data-requests/999999/export",
        "/data-requests/999999/execute-delete",
    ):
        _bad(client, "post", f"{base}/{path.lstrip('/')}", env.ah)


def test_subscriptions_and_b2b(client, env):
    sub = "/api/v1/subscriptions"
    for method, path, payload in (
        ("get", "/plans", None),
        ("post", "/plans", {}),
        ("post", "/subscribe", {}),
        ("get", "/subscriptions", None),
        ("post", "/subscriptions/999999/cancel", None),
        ("post", "/digital-assets", {}),
        ("post", "/digital-assets/999999/download", {}),
        ("post", "/licenses", {}),
    ):
        _bad(client, method, f"{sub}{path}", payload=payload)
    for path in (
        "/plans",
        "/subscribe",
        "/digital-assets",
        "/digital-assets/9/download",
        "/licenses",
    ):
        _bad(client, "post", f"{sub}{path}", env.ah, {})
    b2b = "/api/v1/b2b"
    for method, path, payload in (
        ("get", "/customer-groups", None),
        ("post", "/customer-groups", {}),
        ("post", "/price-lists", {}),
        ("post", "/price-lists/9/items", {}),
        ("post", "/quotes", {}),
        ("post", "/quotes/9/items", {}),
        ("post", "/quotes/9/convert", {}),
        ("get", "/quotes/9", None),
    ):
        _bad(client, method, f"{b2b}{path}", payload=payload)
    for path in (
        "/customer-groups",
        "/price-lists",
        "/price-lists/9/items",
        "/quotes/9/items",
        "/quotes/9/convert",
    ):
        _bad(client, "post", f"{b2b}{path}", env.ah, {})
    _bad(client, "get", f"{b2b}/quotes/9", env.ah)


def test_i18n_and_users(client, env, platform_admin_headers, app):
    i18n = "/api/v1/i18n"
    _bad(client, "get", f"{i18n}/pages/missing")
    _bad(client, "post", f"{i18n}/pages")
    for path in ("/pages/999999", "/pages/999999/translations/ar"):
        _bad(client, "put", f"{i18n}{path}", env.ah, {"title": "x"})
    _bad(client, "delete", f"{i18n}/pages/999999", env.ah)
    _bad(client, "get", f"{i18n}/glossary")
    _bad(client, "post", f"{i18n}/glossary")
    _bad(client, "post", f"{i18n}/pages", env.ah, {})
    with app.app_context():
        page = PageService().create_page(
            tenant_id=env.tid, slug=f"pg-{uuid.uuid4().hex[:6]}", title="Push"
        )
        page_id = page.id
    _bad(client, "put", f"{i18n}/pages/{page_id}/translations/ar", env.ah, {})
    assert client.get(f"{i18n}/pages?all=1", headers=env.ah).status_code == 200
    assert (
        client.post(
            f"{i18n}/glossary",
            headers=env.ah,
            json={
                "source_locale": "ar",
                "target_locale": "en",
                "source_term": "منتج",
                "target_term": "product",
            },
        ).status_code
        == 201
    )
    users, h = "/api/v1/users", platform_admin_headers
    for method, path, payload in (
        ("get", "/", None),
        ("post", "/", {}),
        ("put", "/999999", {}),
        ("delete", "/999999", None),
        ("post", "/not-a-uuid/roles", {}),
    ):
        _bad(client, method, f"{users}{path}", payload=payload)
    _bad(client, "post", f"{users}/", h, {})
    assert (
        client.post(
            f"{users}/",
            headers=h,
            json={
                "email": f"su-{uuid.uuid4().hex[:8]}@test.com",
                "password": "password123",
                "is_superuser": True,
            },
        ).status_code
        == 400  # platform admins are CLI-only (RBAC one-time invariant)
    )
    _bad(
        client,
        "post",
        f"{users}/",
        h,
        {"email": "tenantless@test.com", "password": "password123"},
    )
    _bad(client, "put", f"{users}/999999", h, {})
    _bad(client, "delete", f"{users}/999999", h)
    _bad(client, "post", f"{users}/not-a-uuid/roles", h, {})
    missing = str(uuid.uuid4())
    _bad(client, "post", f"{users}/{missing}/roles", h, {"role_code": "x"})
    _bad(client, "post", f"{users}/{env.buyer_pid}/roles", h, {})
    _bad(
        client,
        "post",
        f"{users}/{env.buyer_pid}/roles",
        h,
        {"role_code": "x", "tenant_id": "bad"},
    )


# webhooks.py
def _stripe(c, tid, payload, secret=SECRET):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return c.post(
        f"/webhooks/stripe/{tid}",
        data=raw,
        content_type="application/json",
        headers={"Stripe-Signature": f"t={ts},v1={sig}"},
    )


def _paypal(c, tid, payload, headers=None, secret=SECRET):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    if headers is None:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        signed = "|".join(["txn-1", ts, "wh-1", raw.decode()]).encode()
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        headers = {
            "Paypal-Auth-Algo": "HMAC-SHA256",
            "Paypal-Cert-Url": "https://api.paypal.com/certs",
            "Paypal-Transmit-Id": "txn-1",
            "Paypal-Transmit-Time": ts,
            "Paypal-Webhook-Id": "wh-1",
            "Paypal-Transmit-Sig": sig,
        }
    return c.post(
        f"/webhooks/paypal/{tid}",
        data=raw,
        content_type="application/json",
        headers=headers,
    )


def _bnpl(c, provider, tid, payload, secret=SECRET):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post(
        f"/webhooks/bnpl/{provider}/{tid}",
        data=raw,
        content_type="application/json",
        headers={"X-Webhook-Signature": sig, "X-Event-Id": uuid.uuid4().hex},
    )


def test_webhook_remaining_branches(client, app, env, claim_cache):
    app.config["WEBHOOK_SECRET"] = SECRET
    tid = env.tid
    event = uuid.uuid4().hex
    assert (
        _stripe(client, tid, {"id": event, "type": "unknown.event"}).status_code == 200
    )
    assert _stripe(client, tid, {"id": event, "type": "unknown.event"}).get_json()[
        "duplicate"
    ]
    assert (
        _stripe(client, 999999, {"id": uuid.uuid4().hex, "type": "x"}).status_code
        != 200
    )
    assert _paypal(client, tid, {"event_type": "x"}, headers={}).status_code == 400
    event = uuid.uuid4().hex
    assert (
        _paypal(client, tid, {"id": event, "event_type": "unknown"}).status_code == 200
    )
    assert _paypal(client, tid, {"id": event, "event_type": "unknown"}).get_json()[
        "duplicate"
    ]
    for et in ("PAYMENT.CAPTURE.REFUNDED", "CHECKOUT.ORDER.APPROVED"):
        assert (
            _paypal(client, tid, {"id": uuid.uuid4().hex, "event_type": et}).status_code
            == 200
        )
    assert (
        _paypal(client, 999999, {"id": uuid.uuid4().hex, "event_type": "x"}).status_code
        != 200
    )
    assert (
        _bnpl(client, "tabby", tid, {"status": "captured"}, secret="bad").status_code
        == 400
    )
    event = uuid.uuid4().hex
    assert (
        _bnpl(client, "tabby", tid, {"id": event, "status": "unknown"}).status_code
        == 200
    )
    assert _bnpl(client, "tabby", tid, {"id": event, "status": "unknown"}).get_json()[
        "duplicate"
    ]
    for status in ("refunded", "authorized"):
        assert (
            _bnpl(
                client, "tabby", tid, {"id": uuid.uuid4().hex, "status": status}
            ).status_code
            == 200
        )
    assert _bnpl(client, "tabby", 999999, {"status": "captured"}).status_code != 200
    assert (
        client.post(
            f"/webhooks/palpay/{tid}", json={"status": "authorized"}
        ).status_code
        == 400
    )
    _bad(client, "post", f"/webhooks/app/{tid}/no-such-topic")
    _bad(client, "post", "/webhooks/app/999999/topic")
    with app.app_context():
        svc = AppPlatformService()
        oauth = svc.register_app(
            tenant_id=tid, name="Push Hook", redirect_uris=["https://x.test/cb"]
        )
        inst = svc.install_app(
            tenant_id=tid, app_id=oauth.id, installed_by=env.admin_id
        )
        sub = svc.subscribe_webhook(
            tenant_id=tid,
            installation_id=inst.id,
            topic="order.created",
            callback_url="https://x.test/hook",
        )
        secret = sub.webhook_secret
    raw = json.dumps({"id": uuid.uuid4().hex}, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    for _ in range(2):
        r = client.post(
            f"/webhooks/app/{tid}/order.created",
            data=raw,
            content_type="application/json",
            headers={"X-Webhook-Signature": sig},
        )
        assert r.status_code == 200, r.get_json()


# catalog / payments / shipping / tax
def test_catalog_payments_shipping_tax(client, env):
    _bad(client, "get", "/api/v1/brands/")
    _bad(client, "post", "/api/v1/brands/")
    _bad(client, "post", "/api/v1/brands/", env.ah, {})
    assert (
        client.post(
            "/api/v1/brands/",
            headers=env.ah,
            json={"name": "Brand", "slug": "dup-brand"},
        ).status_code
        == 201
    )
    _bad(
        client,
        "post",
        "/api/v1/brands/",
        env.ah,
        {"name": "Brand2", "slug": "dup-brand"},
    )
    _bad(client, "get", "/api/v1/categories/")
    _bad(client, "post", "/api/v1/categories/")
    _bad(client, "post", "/api/v1/categories/", env.ah, {})
    _bad(client, "delete", "/api/v1/vouchers/no-such", env.ah)
    _bad(client, "post", "/api/v1/payments/orders/x/pay")
    _bad(client, "post", "/api/v1/payments/x/refund")
    _bad(client, "post", "/api/v1/payments/x/refund", env.ah, {"amount": "bad"})
    _bad(client, "get", "/api/v1/shipping/methods")
    _bad(client, "post", "/api/v1/shipping/methods")
    _bad(client, "post", "/api/v1/shipping/methods", env.ah, {})
    _bad(client, "post", "/api/v1/shipping/calculate")
    _bad(client, "post", "/api/v1/shipping/calculate", env.ah, {})
    _bad(client, "get", "/api/v1/tax/jurisdictions")
    for path in ("/jurisdictions", "/jurisdictions/9/rates"):
        _bad(client, "post", f"/api/v1/tax{path}")
        _bad(client, "post", f"/api/v1/tax{path}", env.ah, {})
    _bad(client, "post", "/api/v1/tax/calculate")
    _bad(client, "post", "/api/v1/tax/calculate", env.sh, {"subtotal": "bad"})


# oms / dropship / returns
def test_fulfillment_and_returns_errors(client, env, app):
    for method, path in (
        ("get", "/dropship/suppliers"),
        ("post", "/dropship/pod"),
        ("post", "/dropship/suppliers"),
        ("post", "/dropship/orders"),
        ("get", "/oms/warehouses"),
        ("post", "/oms/warehouses"),
        ("put", "/oms/inventory"),
        ("post", "/oms/fulfillments"),
        ("post", "/oms/fulfillments/9/ship"),
        ("get", "/oms-ext/transfers"),
        ("post", "/oms-ext/transfers"),
        ("post", "/oms-ext/transfers/9/items"),
        ("post", "/oms-ext/transfers/9/complete"),
        ("get", "/returns/reasons"),
        ("get", "/returns/"),
        ("put", "/returns/9/approve"),
        ("post", "/returns/9/complete"),
    ):
        _bad(client, method, f"/api/v1{path}")
    for method, path in (
        ("post", "/dropship/pod"),
        ("post", "/dropship/suppliers"),
        ("post", "/dropship/orders"),
        ("post", "/oms/warehouses"),
        ("put", "/oms/inventory"),
        ("post", "/oms/fulfillments"),
        ("post", "/oms-ext/transfers"),
        ("post", "/oms-ext/transfers/9/items"),
        ("post", "/returns/"),
    ):
        _bad(client, method, f"/api/v1{path}", env.ah, {})
    pid, oid = _order(env, app, user_id=env.buyer_id)
    with app.app_context():
        order = db.session.get(Order, oid)
        order.payment_status = "paid"
        db.session.commit()
        ret = RmaService().create_return(
            tenant_id=env.tid, order_id=oid, items=[], user_id=env.buyer_id
        )
        rid = ret.id
    _bad(client, "get", f"/api/v1/returns/{rid}", env.oh)
    _bad(client, "post", "/api/v1/returns/", env.oh, {"order_public_id": pid})
    _bad(client, "post", "/api/v1/returns/", env.bh, {})
    _bad(client, "get", "/api/v1/returns/999999", env.bh)


# remaining v2/admin modules
def test_misc_api_validation_branches(client, env):
    for method, path in (
        ("post", "/affiliates/programs"),
        ("post", "/affiliates/register"),
        ("post", "/affiliates/commissions"),
        ("post", "/bundles"),
        ("post", "/bundles/9/items"),
        ("post", "/metafields/definitions"),
        ("post", "/metafields/values"),
        ("get", "/metafields/product/9"),
        ("post", "/live-chat/sessions"),
        ("post", "/live-chat/sessions/9/messages"),
        ("post", "/draft-orders"),
        ("post", "/draft-orders/9/items"),
        ("post", "/draft-orders/9/convert"),
        ("post", "/store-credit/add"),
        ("post", "/store-credit/deduct"),
        ("get", "/store-credit/transactions"),
        ("post", "/stock-notifications"),
        ("post", "/reconciliation/runs/9/items"),
        ("post", "/reconciliation/runs/9/complete"),
        ("get", "/workflow/definitions"),
        ("post", "/workflow/definitions"),
    ):
        _bad(client, method, f"/api/v1{path}")
    h = env.ah
    for path in (
        "/affiliates/programs",
        "/affiliates/register",
        "/affiliates/commissions",
        "/bundles",
        "/bundles/9/items",
        "/metafields/definitions",
        "/metafields/values",
        "/live-chat/sessions/9/messages",
        "/draft-orders/9/items",
        "/store-credit/add",
        "/store-credit/deduct",
        "/reconciliation/runs/9/items",
        "/workflow/definitions",
    ):
        _bad(client, "post", f"/api/v1{path}", h, {})
    assert client.get("/api/v1/metafields/product/9", headers=h).status_code == 200
    _bad(client, "get", "/api/v1/store-credit/transactions?credit_id=bad", h)
    _bad(client, "post", "/api/v1/draft-orders/9/convert", h, {})
    _bad(client, "post", "/api/v1/workflow/definitions/9/run", h, {})
    _bad(client, "get", "/api/v1/platform/stores/999999/financial-report")


def test_platform_admin_error_branches(client):
    for method, path in (
        ("get", "/settings"),
        ("put", "/settings"),
        ("get", "/stats"),
        ("get", "/reconciliation"),
        ("post", "/reconciliation/run"),
    ):
        _bad(client, method, f"/api/v1/platform{path}")


def test_extra_reachable_error_branches(client, env, platform_admin_headers, app):
    _bad(client, "post", "/api/v1/products/", env.ah, {})
    _bad(client, "get", "/api/v1/affiliates/affiliates")
    _bad(client, "get", "/api/v1/affiliates/commissions")
    _bad(
        client,
        "post",
        "/api/v1/compliance/data-requests",
        None,
        {"customer_email": "a@a.test", "request_type": "export"},
    )
    _bad(client, "put", "/api/v1/compliance/cookie-settings")
    _bad(client, "post", "/api/v1/compliance/sso", None, {"provider_type": "x"})
    _bad(client, "post", "/api/v1/i18n/glossary", env.ah, {})
    _bad(client, "get", "/api/v1/live-chat/sessions/9/messages")
    _bad(
        client,
        "post",
        "/api/v1/returns/",
        platform_admin_headers,
        {"order_public_id": "x"},
    )
    _bad(
        client,
        "post",
        "/api/v1/stock-notifications",
        env.sh,
        {"product_id": "x", "customer_email": "a@a.test"},
    )
    assert (
        client.post("/api/v1/store/account/logout", headers=env.bh).status_code == 200
    )
    pid, _ = _order(env, app)
    _bad(client, "get", f"/api/v1/store/orders/{pid}/invoice.pdf", env.ah)
    for path in ("/locations", "/locations/9/slots"):
        _bad(client, "post", f"/api/v1/bopis{path}")
        _bad(client, "post", f"/api/v1/bopis{path}", env.ah, {})
    _bad(client, "post", "/api/v1/accessibility/audits")
    _bad(client, "post", "/api/v1/accessibility/audits", env.ah, {})
    _bad(client, "post", "/api/v1/gift-registries", env.ah, {})
    _bad(client, "post", "/api/v1/gift-registries/no-such/items", env.sh, {})
    with app.app_context():
        reg = GiftRegistryService().create_registry(
            tenant_id=env.tid,
            customer_email=env.buyer_email,
            registry_name="Extra",
            user_id=env.buyer_id,
        )
        slug = reg.slug
    assert (
        client.get(f"/api/v1/gift-registries/{slug}", headers=env.sh).status_code == 200
    )
    _bad(
        client,
        "post",
        f"/api/v1/gift-registries/{slug}/items",
        env.bh,
        {"product_id": "x"},
    )
    _bad(
        client,
        "post",
        f"/api/v1/store/account/gift-registries/{slug}/items",
        env.bh,
        {"product_id": "x"},
    )
    with app.app_context():
        svc = AffiliateService()
        program = svc.create_program(
            tenant_id=env.tid,
            name="P",
            code="p",
            commission_type="percent",
            commission_value="5",
        )
        affiliate = svc.register_affiliate(
            tenant_id=env.tid, program_id=program.id, email="aff@test.com"
        )
        aff_id = affiliate.id
        _, aff_order_id = _order(env, app)
    assert (
        client.post(
            "/api/v1/affiliates/commissions",
            headers=env.ah,
            json={"affiliate_id": aff_id, "order_id": aff_order_id, "amount": "1.00"},
        ).status_code
        == 201
    )
    b = client.post(
        "/api/v1/bundles",
        headers=env.ah,
        json={"name": "B", "slug": "b", "bundle_price": "10.00"},
    )
    assert b.status_code == 201
    assert (
        client.post(
            f"/api/v1/bundles/{b.get_json()['bundle']['id']}/items",
            headers=env.ah,
            json={"product_id": env.pid},
        ).status_code
        == 201
    )
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "x@y.z", "password": "bad", "tenant_id": env.tid},
    ).status_code in (400, 401)
    _bad(client, "post", "/api/v1/auth/sso/exchange", None, {})
    assert (
        client.post(
            "/api/v1/auth/sso/exchange",
            json={
                "tenant_id": env.tid,
                "provider_code": "x",
                "external_email": "x@y.z",
            },
        ).status_code
        != 200
    )


# fmt: on
