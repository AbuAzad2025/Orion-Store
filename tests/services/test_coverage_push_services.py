"""Real-DB coverage push for 04-SERVICES modules.

Persistence is always the real PostgreSQL test database. Provider HTTP is the
only external boundary: adapters monkeypatch the imported ``_http`` request
function, and ``_http`` itself monkeypatches ``requests.post``. Business logic
and ORM sessions are never mocked.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from i18n_svc.i18n_service import I18nService
from i18n_svc.translation_service import TranslationService
from shipping_svc.shipping_service import ShippingService
from stock_notification.stock_notification import StockNotification
from webhook_svc import verification_service, webhook_handler
from webhook_svc.verification_service import WebhookVerificationService
from workflow_svc.workflow_service import WorkflowService

from b2b_svc.b2b_service import B2bService
from bnpl.bnpl_provider import BnplProvider
from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.crypto import CryptoService
from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.utils import utc_now
from integrations.payments import _http
from integrations.payments import bnpl as bnpl_adapter
from integrations.payments import palpay, paypal, stripe_connect
from oms_svc.oms_service import OmsService
from order.cart import CartItem
from order.order import Order, OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from payment_svc.payment_service import PaymentService
from platform_models.tenant_gateway import TenantPaymentGateway
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

A = Decimal("25.00")


def _row(cls, **kw):
    row = cls(**kw)
    db.session.add(row)
    db.session.commit()
    return row


def _seq(*items):
    rest = iter(items)

    def next_item(*a, **k):
        item = next(rest)
        if isinstance(item, BaseException):
            raise item
        return item

    return next_item


def _fixed(item):
    return lambda *a, **k: item


def _raises(exc):
    def raise_it(*a, **k):
        raise exc

    return raise_it


def _ok(data):
    return {"success": True, "data": data}


def _bad(error):
    return {"success": False, "error": error}


def _fails(exc, fn, *args, **kw):
    with pytest.raises(exc):
        fn(*args, **kw)


@pytest.fixture
def tenant(app):
    t = uuid.uuid4().hex[:10]
    return TenantService().create_tenant(
        name=f"Push {t}", slug=f"push-{t}", email=f"push-{t}@test.com"
    )


@pytest.fixture
def product(tenant):
    return ProductService().create(
        tenant_id=tenant.id,
        name="Push Widget",
        slug=f"push-widget-{tenant.id}",
        price="25.00",
        quantity=20,
        is_published=True,
    )


@pytest.fixture
def live(app, monkeypatch):
    monkeypatch.setitem(app.config, "PAYMENT_LIVE_CALLS_ENABLED", True)
    return app


@pytest.fixture
def no_stub(app, monkeypatch):
    monkeypatch.setitem(app.config, "PAYMENT_STUB_ALLOWED", False)
    return app


def _creds(app, row, **payload):
    enc = CryptoService(app.config["ENCRYPTION_KEY"]).encrypt(json.dumps(payload))
    if isinstance(row, BnplProvider):
        row.api_credentials_encrypted = enc
    else:
        row.credentials_encrypted = enc
    db.session.commit()


def _gw(t, provider, *, sandbox=True, secret=None):
    return _row(
        TenantPaymentGateway,
        tenant_id=t,
        provider=provider,
        display_name=provider,
        is_enabled=True,
        is_sandbox=sandbox,
        status="active",
        webhook_secret=secret,
        config={},
    )


def _bnpl(t, *, sandbox=True):
    return _row(
        BnplProvider,
        tenant_id=t,
        provider="tabby",
        is_enabled=True,
        config={"is_sandbox": sandbox},
    )


def _order(t, *, status="pending", paid=False, total="25.00"):
    return _row(
        Order,
        tenant_id=t,
        order_number=f"PS-{uuid.uuid4().hex[:8]}",
        customer_email="buyer@push.test",
        shipping_address={},
        subtotal=total,
        total=total,
        status=status,
        payment_status="paid" if paid else "pending",
    )


def _pay(t, order, *, provider="cod", status="completed", pid=None):
    return _row(
        Payment,
        tenant_id=t,
        order_id=order.id,
        amount=order.total,
        currency="ILS",
        payment_method=provider,
        payment_provider=provider,
        status=status,
        provider_payment_id=pid,
    )


def _checkout(tenant, product):
    PlatformSettingsService().ensure_seeded()
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="Buyer@Push.Test",
        shipping_address={"city": "Ramallah"},
    )


def _charge(mod, order, row):
    if mod is paypal:
        return mod.charge_paypal(order=order, gateway=row, amount=A)
    if mod is palpay:
        return mod.charge_palpay(order=order, gateway=row, amount=A)
    return mod.charge_bnpl(order=order, provider_row=row, amount=A)


def _refund(mod, payment, row):
    if mod is bnpl_adapter:
        return mod.refund_payment(payment=payment, provider_row=row, amount=A)
    return mod.refund_payment(payment=payment, gateway=row, amount=A)


class _Resp:
    def __init__(self, payload=None, status=200, bad_json=False) -> None:
        self.status_code = status
        self.payload = payload
        self.bad_json = bad_json

    def json(self):
        if self.bad_json:
            raise ValueError("invalid")
        return self.payload


ADAPTERS = [(paypal, "gw"), (palpay, "gw"), (bnpl_adapter, "bnpl")]


def test_http_boundary_outcomes(monkeypatch):
    cfg = SimpleNamespace(
        config={"api_base_url": "https://cfg.test/v1/"}, is_sandbox=True
    )
    assert _http.endpoint_for(cfg, "PUSH_URL", "s", "l") == "https://cfg.test/v1"
    monkeypatch.setenv("PUSH_URL", "https://env.test/")
    plain = SimpleNamespace(config={}, is_sandbox=False)
    assert _http.endpoint_for(plain, "PUSH_URL", "s", "l") == "https://env.test"
    kw = dict(payload={}, headers={}, idempotency="k")
    replies = (
        requests.ConnectionError(),
        _Resp(status=400),
        _Resp(bad_json=True),
        _Resp([]),
    )
    for reply in replies:
        monkeypatch.setattr(requests, "post", _seq(reply))
        assert _http.post_json("u", **kw)["error"]
    for reply in (*replies, _Resp([1])):
        monkeypatch.setattr(requests, "post", _seq(reply))
        assert _http.post_form("u", data={}, headers={}, idempotency="k")["error"]
    assert _http.provider_refund_id({"refund": {"id": "rf"}}) == "rf"
    assert _http.provider_payment_id({"payment_intent": {"id": "pi"}}) == "pi"


@pytest.mark.parametrize("mod,factory", ADAPTERS)
def test_adapter_live_charge_branches(app, live, tenant, monkeypatch, mod, factory):
    t = tenant.id
    order = _order(t)
    row = (
        _gw(t, mod.__name__.split(".")[-1], sandbox=False)
        if factory == "gw"
        else _bnpl(t, sandbox=False)
    )
    charge = lambda: _charge(mod, order, row)
    assert "credentials_missing" in charge()["error"]
    _creds(app, row, other="x")
    assert "credentials_missing" in charge()["error"]
    _creds(app, row, client_id="cid", client_secret="sec", api_key="key")
    if mod is paypal:
        monkeypatch.setattr(
            mod,
            "post_form",
            _seq(_bad("x"), _ok({}), *[_ok({"access_token": "tok"})] * 6),
        )
        errors = (
            "paypal_auth_failed",
            "paypal_auth_failed",
            "provider_http_400",
            "paypal_order_id_missing",
            "capture failed",
        )
        monkeypatch.setattr(
            mod,
            "post_json",
            _seq(
                _bad("provider_http_400"),
                _ok({}),
                _ok({"id": "o1"}),
                _bad("capture failed"),
                _ok({"id": "o2"}),
                _ok({"id": "o3"}),
            ),
        )
    else:
        errors = (
            "provider_http_400",
            (
                ("bnpl" if mod is bnpl_adapter else "palpay")
                + "_missing_transaction_id"
                if mod is bnpl_adapter
                else "palpay_missing_payment_id"
            ),
        )
        monkeypatch.setattr(
            mod,
            "post_json",
            _seq(_bad("provider_http_400"), _ok({}), _ok({"id": "txn"})),
        )
    for expected in errors:
        assert expected in charge().get("error", "")
    assert charge()["success"] is True


@pytest.mark.parametrize("mod,factory", ADAPTERS)
def test_adapter_live_refund_branches(app, live, tenant, monkeypatch, mod, factory):
    t = tenant.id
    row = (
        _gw(t, mod.__name__.split(".")[-1], sandbox=False)
        if factory == "gw"
        else _bnpl(t, sandbox=False)
    )
    payment = _pay(t, _order(t), provider="x", pid="txn")
    refund = lambda: _refund(mod, payment, row)
    assert "credentials_missing" in refund()["error"]
    _creds(app, row, client_id="cid", client_secret="sec", api_key="key")
    if mod is paypal:
        monkeypatch.setattr(
            mod, "post_form", _seq(_bad("x"), *[_ok({"access_token": "tok"})] * 6)
        )
    monkeypatch.setattr(
        mod,
        "post_json",
        _seq(_bad("provider_http_500"), _ok({}), _ok({"refund_id": "re-1"})),
    )
    if mod is paypal:
        assert refund()["error"] == "paypal_auth_failed"
    assert refund()["error"] == "provider_http_500"
    assert "missing_refund_id" in refund()["error"]
    assert refund()["provider_refund_id"] == "re-1"


def test_non_sandbox_stub_guards(app, tenant, no_stub):
    t = tenant.id
    for mod, factory in ADAPTERS:
        row = (
            _gw(t, mod.__name__.split(".")[-1], sandbox=False)
            if factory == "gw"
            else _bnpl(t, sandbox=False)
        )
        order = _order(t)
        _creds(app, row, api_key="key", client_id="cid", client_secret="sec")
        assert "credentials_missing" in _charge(mod, order, row)["error"]
        payment = _pay(t, order, provider="x")
        assert _refund(mod, payment, row)["provider_refund_id"]
    stripe_row = _gw(t, "stripe", sandbox=False)
    _creds(app, stripe_row, secret_key="sk")
    assert (
        stripe_connect.charge_stripe(order=_order(t), gateway=stripe_row, amount=A)[
            "error"
        ]
        == "stripe_credentials_missing"
    )


def test_stripe_live_error_branches(app, live, tenant, monkeypatch):
    t = tenant.id
    row = _gw(t, "stripe", sandbox=False)
    order = _order(t)
    charge = lambda: stripe_connect.charge_stripe(order=order, gateway=row, amount=A)
    assert charge()["error"] == "stripe_credentials_missing"
    _creds(app, row, other="x")
    assert charge()["error"] == "stripe_credentials_missing"
    _creds(app, row, secret_key="sk")
    monkeypatch.setattr(stripe_connect, "post_form", _fixed(_ok({})))
    assert charge()["error"] == "stripe_missing_payment_id"
    payment = _pay(t, order, provider="stripe", pid="pi-1")
    _creds(app, row, other="x")
    refund = lambda: stripe_connect.refund_payment(
        payment=payment, gateway=row, amount=A
    )
    assert refund()["error"] == "stripe_credentials_missing"
    _creds(app, row, secret_key="sk")
    monkeypatch.setattr(
        stripe_connect, "post_form", _seq(_bad("provider_http_500"), _ok({}))
    )
    assert refund()["error"] == "provider_http_500"
    assert refund()["error"] == "stripe_missing_refund_id"


def test_pay_order_charge_failure_modes(app, live, tenant, product, monkeypatch):
    t = tenant.id
    row = _gw(t, "stripe", sandbox=False)
    _creds(app, row, secret_key="sk")
    order = _checkout(tenant, product)
    _pay(t, order, status="pending")
    svc = PaymentService()
    _fails(
        ConflictError, svc.pay_order, tenant_id=t, order_public_id=str(order.public_id)
    )
    offline = {"success": False, "uncertain": True, "error": "offline"}
    monkeypatch.setattr(stripe_connect, "post_form", _fixed(offline))
    uncertain = _checkout(tenant, product)
    _fails(
        ConflictError,
        svc.pay_order,
        tenant_id=t,
        order_public_id=str(uncertain.public_id),
        payment_method="stripe",
    )
    assert Payment.query.filter_by(order_id=uncertain.id).one().status == "pending"
    monkeypatch.setattr(stripe_connect, "post_form", _fixed(_bad("declined")))
    failed = _checkout(tenant, product)
    _fails(
        ValidationError,
        svc.pay_order,
        tenant_id=t,
        order_public_id=str(failed.public_id),
        payment_method="stripe",
    )
    assert Payment.query.filter_by(order_id=failed.id).one().status == "failed"


def test_pay_order_provider_dispatch_and_guards(app, tenant, product):
    t = tenant.id
    for provider in ("stripe", "palpay", "bnpl_tabby"):
        _gw(t, provider)
    _bnpl(t)
    for method in ("stripe", "palpay", "bnpl_tabby"):
        order = _checkout(tenant, product)
        result = PaymentService().pay_order(
            tenant_id=t, order_public_id=str(order.public_id), payment_method=method
        )
        assert result["payment"]["status"] == "completed"
    svc = PaymentService()
    _fails(ValidationError, svc._validate_payment_request, _order(t, paid=True))
    _fails(
        ValidationError, svc._validate_payment_request, _order(t, status="cancelled")
    )
    order = _order(t)
    gateway = _gw(t, "mystery")
    assert svc._charge_external_gateway(
        order, gateway, _pay(t, order, status="pending")
    ) == _bad("unsupported_provider")


def test_refund_validation_and_uncertain_result(app, live, tenant, monkeypatch):
    t = tenant.id
    svc = PaymentService()
    _fails(NotFoundError, svc.refund, tenant_id=t, payment_public_id="bad")
    _fails(NotFoundError, svc.refund, tenant_id=t, payment_public_id=str(uuid.uuid4()))
    order = _order(t)
    payment = _pay(t, order, status="pending")
    _fails(
        ValidationError,
        svc.refund,
        tenant_id=t,
        payment_public_id=str(payment.public_id),
    )
    payment.status = "completed"
    db.session.commit()
    _fails(
        ValidationError,
        svc.refund,
        tenant_id=t,
        payment_public_id=str(payment.public_id),
        amount="abc",
    )
    row = _gw(t, "stripe", sandbox=False)
    _creds(app, row, secret_key="sk")
    payment.payment_provider, payment.provider_payment_id = "stripe", "pi-1"
    db.session.commit()
    offline = {"success": False, "uncertain": True, "error": "offline"}
    monkeypatch.setattr(stripe_connect, "post_form", _fixed(offline))
    _fails(
        ConflictError, svc.refund, tenant_id=t, payment_public_id=str(payment.public_id)
    )
    assert Refund.query.filter_by(payment_id=payment.id).one().status == "pending"
    declined = _pay(t, _order(t), provider="stripe", pid="pi-2")
    monkeypatch.setattr(stripe_connect, "post_form", _fixed(_bad("declined")))
    _fails(
        ValidationError,
        svc.refund,
        tenant_id=t,
        payment_public_id=str(declined.public_id),
    )


def test_refund_gateway_dispatch(app, live, tenant, monkeypatch):
    t = tenant.id
    svc = PaymentService()
    payment = _pay(t, _order(t), provider="bnpl_tabby", pid="txn")
    refund = lambda: svc._refund_external_gateway(t, payment, Decimal("5"))
    monkeypatch.setitem(app.config, "PAYMENT_LIVE_CALLS_ENABLED", False)
    assert refund()["success"] is True
    _creds(app, _bnpl(t), api_key="key")
    monkeypatch.setattr(bnpl_adapter, "post_json", _fixed(_ok({"refund_id": "ok"})))
    monkeypatch.setitem(app.config, "PAYMENT_LIVE_CALLS_ENABLED", True)
    assert refund()["provider_refund_id"] == "ok"
    payment.payment_provider = "mystery"
    db.session.commit()
    assert refund()["error"] == "unsupported_provider"
    _fails(NotFoundError, svc._refund_gateway, t, "stripe")
    gw = _gw(t, "bnpl_tabby")
    row = BnplProvider.query.filter_by(tenant_id=t, provider="tabby").one()
    _creds(app, row, api_key="key")
    monkeypatch.setattr(bnpl_adapter, "post_json", _fixed(_bad("declined")))
    order = _order(t)
    queued = _pay(t, order, status="pending")
    assert svc._charge_external_gateway(order, gw, queued) == _bad("declined")


def test_workflow_trigger_shapes_conditions_and_idempotency(app, tenant):
    t = tenant.id
    svc = WorkflowService()
    assert svc.trigger() == []
    wf = svc.create_definition(
        tenant_id=t,
        name="Cond",
        trigger_event="order.paid",
        actions=[],
        conditions={"tier": ["gold"], "channel": "web"},
    )
    payload = {"tier": "gold", "channel": "web"}
    assert (
        svc.trigger(
            event="order.paid",
            event_id=1,
            tenant_id=t,
            payload={"tier": "silver", "channel": "web"},
        )
        == []
    )
    assert (
        svc.trigger(
            event="order.paid",
            event_id=2,
            tenant_id=t,
            payload={"tier": "gold", "channel": "app"},
        )
        == []
    )
    missing_key = {"tier": "gold"}
    assert (
        len(
            svc.trigger(
                event="order.paid", event_id=5, tenant_id=t, payload=missing_key
            )
        )
        == 1
    )
    runs = svc.trigger(event="order.paid", event_id=3, tenant_id=t, payload=payload)
    assert len(runs) == 1 and runs[0].status == "completed"
    legacy = {"tenant_id": t, **payload, "event_id": 4}
    assert len(svc.trigger(event="order.paid", payload=legacy)) == 1
    assert svc.trigger(event="order.paid", payload=legacy) == []
    assert (
        svc.run_definition(wf, t, payload={"event_id": 3, **payload}).id == runs[0].id
    )


def test_workflow_action_failure_and_ignored_actions(app, tenant, monkeypatch):
    from notification_svc.notification_service import NotificationService

    t = tenant.id
    svc = WorkflowService()
    wf = svc.create_definition(
        tenant_id=t,
        name="Actions",
        trigger_event="order.paid",
        actions=[{"type": "send_email", "recipient": "x@push.test"}],
    )
    monkeypatch.setattr(
        NotificationService, "send_action_email", _raises(RuntimeError("smtp offline"))
    )
    failed = svc.trigger("order.paid", t, {"event_id": 11})
    assert failed[0].status == "failed" and "smtp offline" in failed[0].error_message
    wf.actions = ["skip", {"type": "tag_order"}]
    db.session.commit()
    assert svc.trigger("order.paid", t, {"event_id": 12})[0].status == "completed"
    wf.actions = [{"type": "tag_order", "tag": "vip"}]
    db.session.commit()
    assert (
        svc.trigger("order.paid", t, {"event_id": 13, "order_id": 999999})[0].status
        == "completed"
    )


def test_checkout_empty_cart_default_shipping_and_stock_guards(app, tenant, product):
    t = tenant.id
    cart = CartService().get_or_create_cart(tenant_id=t)
    _fails(
        ValidationError,
        CheckoutService().checkout,
        cart=cart,
        customer_email="a@b.test",
        shipping_address={},
    )
    PlatformSettingsService().ensure_seeded()
    ShippingService().create_method(
        tenant_id=t, name="Standard", code="standard", is_default=True
    )
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    foreign = TenantService().create_tenant(
        name="Foreign", slug=f"foreign-{t}", email=f"foreign-{t}@test.com"
    )
    ghost = ProductService().create(
        tenant_id=foreign.id, name="Ghost", slug=f"ghost-{t}", price="1", quantity=1
    )
    CartItem.query.filter_by(cart_id=cart.id).one().product_id = ghost.id
    db.session.commit()
    _fails(
        ValidationError,
        CheckoutService().checkout,
        cart=cart,
        customer_email="a@b.test",
        shipping_address={},
    )
    restored = ProductService().create(
        tenant_id=t,
        name="Restored",
        slug=f"r-{t}",
        price="25.00",
        quantity=1,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=t)
    CartService().add_item(cart=cart, product_id=restored.id, quantity=1)
    restored.quantity = 0
    db.session.commit()
    _fails(
        ValidationError,
        CheckoutService().checkout,
        cart=cart,
        customer_email="a@b.test",
        shipping_address={},
    )


def test_checkout_warehouse_sync_failure_is_non_fatal(
    app, tenant, product, monkeypatch
):
    monkeypatch.setattr(
        OmsService, "sync_product_to_warehouse", _raises(RuntimeError("offline"))
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart, customer_email="a@b.test", shipping_address={}
    )
    assert order.status == "pending" and cart.status == "converted"


def test_b2b_validation_branches(app, tenant, product):
    t = tenant.id
    svc = B2bService()
    _fails(NotFoundError, svc.add_group_member, tenant_id=t, group_id=999, user_id=1)
    _fails(
        NotFoundError,
        svc.add_price_item,
        tenant_id=t,
        price_list_id=999,
        product_id=product.id,
        price="1",
    )
    _fails(
        NotFoundError, svc.resolve_unit_price, tenant_id=t, product_id=999, quantity=1
    )
    _fails(
        NotFoundError,
        svc.add_quote_item,
        tenant_id=t,
        quote_id=999,
        product_id=product.id,
        quantity=1,
    )
    _fails(
        NotFoundError,
        svc.convert_quote_to_order,
        tenant_id=t,
        quote_id=999,
        customer_email="a@b.test",
    )
    quote = svc.create_quote(tenant_id=t)
    for status, match in (
        ("cancelled", "not editable"),
        ("converted", "already converted"),
        ("draft", "no items"),
    ):
        quote.status = status
        db.session.commit()
        fn = svc.add_quote_item if status == "cancelled" else svc.convert_quote_to_order
        kw = (
            dict(quote_id=quote.id, product_id=product.id, quantity=1)
            if status == "cancelled"
            else dict(quote_id=quote.id, customer_email="a@b.test")
        )
        with pytest.raises(ValidationError, match=match):
            fn(tenant_id=t, **kw)


def test_b2b_convert_stock_and_sync_failure(app, tenant, product, monkeypatch):
    t = tenant.id
    svc = B2bService()
    quote = svc.create_quote(tenant_id=t)
    svc.add_quote_item(
        tenant_id=t, quote_id=quote.id, product_id=product.id, quantity=2
    )
    product.quantity = 1
    db.session.commit()
    _fails(
        ValidationError,
        svc.convert_quote_to_order,
        tenant_id=t,
        quote_id=quote.id,
        customer_email="a@b.test",
    )
    product.quantity = 10
    db.session.commit()
    monkeypatch.setattr(
        OmsService, "sync_product_to_warehouse", _raises(RuntimeError("offline"))
    )
    order = svc.convert_quote_to_order(
        tenant_id=t, quote_id=quote.id, customer_email="a@b.test"
    )
    assert OrderItem.query.filter_by(order_id=order.id).count() == 1
    assert quote.status == "converted"


def test_oms_error_branches(app, tenant, product):
    t = tenant.id
    svc = OmsService()
    empty = TenantService().create_tenant(
        name="No WH", slug=f"no-wh-{t}", email=f"no-wh-{t}@test.com"
    )
    _fails(NotFoundError, svc.get_default_warehouse, empty.id)
    _fails(
        NotFoundError,
        svc.upsert_inventory,
        tenant_id=t,
        warehouse_id=999,
        product_id=product.id,
        quantity=1,
    )
    _fails(NotFoundError, svc.create_fulfillment, tenant_id=t, order_id=999)
    order = _order(t)
    _fails(ValidationError, svc.create_fulfillment, tenant_id=t, order_id=order.id)
    order.payment_status = "paid"
    db.session.commit()
    _fails(
        NotFoundError,
        svc.create_fulfillment,
        tenant_id=t,
        order_id=order.id,
        warehouse_id=999,
    )
    no_wh_order = _order(empty.id, paid=True)
    _fails(
        NotFoundError,
        svc.create_fulfillment,
        tenant_id=empty.id,
        order_id=no_wh_order.id,
    )
    _fails(NotFoundError, svc.ship_fulfillment, tenant_id=t, fulfillment_id=999)
    _fails(NotFoundError, svc.sync_product_to_warehouse, tenant_id=t, product_id=999)
    wh = svc.create_warehouse(tenant_id=t, name="Main", code="main")
    fulfillment = svc.create_fulfillment(
        tenant_id=t, order_id=order.id, warehouse_id=wh.id
    )
    shipped = svc.ship_fulfillment(tenant_id=t, fulfillment_id=fulfillment.id)
    assert shipped.status == "shipped"
    _fails(
        ValidationError,
        svc.ship_fulfillment,
        tenant_id=t,
        fulfillment_id=fulfillment.id,
    )


def test_translation_duplicate_slug_and_localized_slug_guards(app, tenant, product):
    t = tenant.id
    I18nService().ensure_locales_seeded()
    svc = TranslationService()
    first = CategoryService().create(tenant_id=t, name="First", slug="cat-first")
    second = CategoryService().create(tenant_id=t, name="Second", slug="cat-second")
    _fails(
        ValidationError,
        svc.upsert_category_translation,
        tenant_id=t,
        category=second,
        locale="en",
        name="EN",
        slug="cat-first",
    )
    for resolver, missing in (
        (svc.get_product_by_localized_slug, "absent-product"),
        (svc.get_category_by_localized_slug, "absent-category"),
    ):
        for locale in ("ar", "en"):
            _fails(NotFoundError, resolver, t, missing, locale)
    svc.upsert_product_translation(
        tenant_id=t, product=product, locale="en", name="EN", slug="p-en"
    )
    svc.upsert_category_translation(
        tenant_id=t, category=first, locale="en", name="EN", slug="c-en"
    )
    product.deleted_at = first.deleted_at = utc_now()
    db.session.commit()
    _fails(NotFoundError, svc.get_product_by_localized_slug, t, "p-en", "en")
    _fails(NotFoundError, svc.get_category_by_localized_slug, t, "c-en", "en")


def test_product_service_guards_and_restock_notification(
    app, tenant, product, monkeypatch
):
    from stock_notification_svc.stock_notification_service import (
        StockNotificationService,
    )

    t = tenant.id
    svc = ProductService()
    _fails(
        ValidationError,
        svc.create,
        tenant_id=t,
        name="X",
        slug="px-1",
        price="1",
        category_id=999,
    )
    _fails(
        ValidationError,
        svc.create,
        tenant_id=t,
        name="X",
        slug="px-2",
        price="1",
        brand_id=999,
    )
    _fails(NotFoundError, svc.get_by_slug, t, "missing")
    _fails(NotFoundError, svc.get_by_public_id, t, "not-a-uuid")
    monkeypatch.setattr(
        OmsService, "sync_product_to_warehouse", _raises(RuntimeError("offline"))
    )
    other = svc.create(tenant_id=t, name="Other", slug=f"other-{t}", price="1")
    _fails(ValidationError, svc.update, other, slug=product.slug)
    product.quantity = 0
    db.session.commit()
    _row(
        StockNotification,
        tenant_id=t,
        product_id=product.id,
        customer_email="restock@test.com",
    )
    monkeypatch.setattr(
        StockNotificationService,
        "notify_for_product",
        _raises(RuntimeError("mail off")),
    )
    assert svc.update(product, quantity=5).quantity == 5
    assert (
        StockNotification.query.filter_by(product_id=product.id).one().is_notified
        is False
    )


def test_verification_secret_timestamp_and_replay_guards(app, tenant, monkeypatch):
    t = tenant.id
    svc = WebhookVerificationService()
    gateway = _gw(t, "stripe", secret="gw-secret")
    assert svc.get_secret(t, "stripe") == gateway.webhook_secret
    monkeypatch.setitem(app.config, "ENV", "production")
    assert svc.get_secret(t + 999, "stripe") is None
    assert svc._paypal_timestamp_fresh("2020-01-01T00:00:00") is False
    assert svc._paypal_timestamp_fresh("not-a-time") is False
    assert svc._paypal_cert_url_allowed("https://api-m.paypal.com:8443/cert") is False
    assert svc._paypal_cert_url_allowed("http://[::1") is False
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    keys = verification_service._PAYPAL_REQUIRED_HEADERS
    headers = dict(
        zip(
            keys,
            (
                "SHA256withRSA",
                "https://api-m.paypal.com/cert",
                "t-1",
                now,
                "!!!bad!!!",
                "w-1",
            ),
        )
    )
    assert svc.verify_paypal_signature(b"{}", headers, "unused") is False
    public_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    monkeypatch.setattr(
        x509,
        "load_pem_x509_certificate",
        _fixed(SimpleNamespace(public_key=lambda: public_key)),
    )
    monkeypatch.setattr(svc, "_fetch_paypal_certificate", _fixed(b"pem"))
    headers["paypal-transmit-sig"] = base64.b64encode(b"sig").decode()
    assert svc.verify_paypal_signature(b"{}", headers, "unused") is False
    monkeypatch.setitem(app.config, "ENV", "testing")
    headers.update({"paypal-auth-algo": "HMAC-SHA256", "paypal-transmit-time": now})
    assert svc.verify_paypal_signature(b"{}", headers, "") is False
    assert svc.claim_webhook_event("stripe", None) is True
    cache = SimpleNamespace(available=True, set_nx=lambda k, v: k.endswith("evt-1"))
    monkeypatch.setitem(app.extensions, "redis_cache", cache)
    assert svc.claim_webhook_event("stripe", "evt-1") is True
    assert svc.claim_webhook_event("stripe", "evt-2") is False


def test_webhook_handler_payload_and_resolution_edges(app, tenant):
    t = tenant.id
    svc = webhook_handler.WebhookEffectHandler()
    assert webhook_handler._refund_amount(
        {"data": {"object": {"amount_refunded": 350}}}, "stripe"
    ) == Decimal("3.50")
    assert webhook_handler._refund_amount(
        {"resource": {"amount": {"value": "9.50"}}}, "paypal"
    ) == Decimal("9.50")
    assert webhook_handler._refund_amount({"refund_amount": "4.00"}, "bnpl") == Decimal(
        "4.00"
    )
    assert (
        webhook_handler._provider_refund_id({"metadata": {"refund_id": "rf-2"}})
        == "rf-2"
    )
    assert webhook_handler._provider_refund_id({"refund": {"id": "rf-3"}}) == "rf-3"
    order = _order(t)
    payment = _pay(t, order, pid="pi-1")
    fallback = {"order_public_id": "bad", "custom_id": str(order.public_id)}
    assert svc._resolve_order(t, fallback) == order
    assert (
        svc._resolve_payment(t, {"payment_public_id": "bad"}, statuses=("completed",))
        is None
    )
    assert svc._resolve_payment(t, {}, statuses=("completed",)) is None
    by_provider = {"resource": {"provider_payment_id": "pi-1"}}
    assert svc._resolve_payment(t, by_provider, statuses=("completed",)) == payment
    payload = {
        "metadata": {
            "payment_public_id": str(payment.public_id),
            "amount_refunded": "NaN",
        }
    }
    assert svc.handle_refund(t, payload)["processed"] is True
    assert Refund.query.filter_by(payment_id=payment.id).one().amount == payment.amount
    negative = _pay(t, _order(t), pid="pi-2")
    payload = {
        "metadata": {
            "payment_public_id": str(negative.public_id),
            "amount_refunded": "-5",
        }
    }
    assert svc.handle_refund(t, payload)["processed"] is True
