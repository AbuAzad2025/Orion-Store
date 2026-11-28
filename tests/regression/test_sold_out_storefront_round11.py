"""Round-11 regression: zero-stock PDP renders sold-out; cart.js ignores it."""

from __future__ import annotations

import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from catalog_svc.product_service import ProductService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from orion.extensions import db
from support.http import tenant_headers
from tenant.tenant import Tenant
from tenant_svc.tenant_service import TenantService

PHONE = "+970501234567"
AR_SOLD, AR_ADD, AR_WA = "نفد المخزون", "أضف إلى السلة", "اطلب عبر واتساب"
EN_SOLD, EN_ADD = "Sold out", "Add to cart"
CART_JS = (
    Path(__file__).resolve().parents[2]
    / "06-STOREFRONT/themes/default/static/js/cart.js"
)


@pytest.fixture(autouse=True)
def _guard_not_live_db(database_url: str) -> None:
    url = database_url.lower()
    assert ":memory:" in url or "test" in url, (
        "Refusing to seed round-11 fixtures on a non-test database: "
        f"{database_url!r}"
    )


@pytest.fixture
def sold_out_store(app):
    with app.app_context():
        tenant = TenantService().create_tenant(
            name="Soldout R11", slug="soldout-r11", email="soldout@test.com"
        )
        FeatureFlagService().set_tenant_override(
            tenant_id=tenant.id, code="multi_language", value=True
        )
        db.session.get(Tenant, tenant.id).phone = PHONE
        db.session.commit()
        zero = ProductService().create(
            tenant_id=tenant.id,
            name="Zero Stock Widget",
            slug="zero-stock-widget",
            price="19.99",
            quantity=0,
            is_published=True,
        )
        control = ProductService().create(
            tenant_id=tenant.id,
            name="In Stock Widget",
            slug="in-stock-widget",
            price="9.99",
            quantity=5,
            is_published=True,
        )
        return SimpleNamespace(
            tenant_id=tenant.id,
            zero_id=zero.id,
            control_id=control.id,
            zero_slug=zero.slug,
            control_slug=control.slug,
            headers=tenant_headers(tenant.slug),
        )


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _find(html, tag=None, **matching):
    p = _Tags()
    p.feed(html)
    return [
        a
        for t, a in p.tags
        if (tag is None or t == tag) and all(a.get(k) == v for k, v in matching.items())
    ]


def _add_buttons(html, product):
    return [
        a for a in _find(html, "button") if a.get("data-add-cart") == str(product if isinstance(product, int) else product.id)
    ]


def _pdp(client, slug, store, locale=None):
    suffix = f"?locale={locale}" if locale else ""
    return client.get(f"/product/{slug}{suffix}", headers=store.headers)


def test_sold_out_buttons_disabled_with_ar_label(client, sold_out_store):
    resp = _pdp(client, sold_out_store.zero_slug, sold_out_store)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    buttons = _add_buttons(html, sold_out_store.zero_id)
    assert len(buttons) == 2
    for btn in buttons:
        assert "disabled" in btn
        assert btn["aria-label"] == f"{AR_SOLD} Zero Stock Widget"
        assert AR_ADD not in btn["aria-label"]
    assert AR_ADD not in html
    assert html.count(AR_SOLD) >= 4


def test_sold_out_english_locale_labels(client, sold_out_store):
    html = _pdp(client, sold_out_store.zero_slug, sold_out_store, locale="en").get_data(
        as_text=True
    )
    buttons = _add_buttons(html, sold_out_store.zero_id)
    assert len(buttons) == 2
    for btn in buttons:
        assert "disabled" in btn
        assert btn["aria-label"] == f"{EN_SOLD} Zero Stock Widget"
    assert EN_ADD not in html


def test_sold_out_hides_whatsapp_order_cta(client, sold_out_store):
    html = _pdp(client, sold_out_store.zero_slug, sold_out_store).get_data(as_text=True)
    assert _find(html, "a", **{"data-wa-product": str(sold_out_store.zero_id)}) == []
    assert AR_WA not in html
    assert "wa.me/?text=" in html  # share link legitimately remains


def test_in_stock_control_keeps_enabled_buttons_and_whatsapp(client, sold_out_store):
    resp = _pdp(client, sold_out_store.control_slug, sold_out_store)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    buttons = _add_buttons(html, sold_out_store.control_id)
    assert len(buttons) == 2
    for btn in buttons:
        assert "disabled" not in btn
        assert btn["aria-label"] == f"{AR_ADD} In Stock Widget"
    wa = _find(html, "a", **{"data-wa-product": str(sold_out_store.control_id)})
    assert len(wa) == 1
    assert wa[0]["href"].startswith("https://wa.me/970501234567")


NODE_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const [cartPath, productId] = process.argv.slice(1);
const source = fs.readFileSync(cartPath, 'utf8');
const calls = [];
const storage = {};
let domReady = null;
const buttons = [];
function makeButton(disabled) {
  return {
    dataset: { addCart: productId }, disabled, textContent: 'Add',
    classList: { add() {}, remove() {} }, handler: null,
    addEventListener(type, fn) { if (type === 'click') this.handler = fn; },
  };
}
buttons.push(makeButton(true));
buttons.push(makeButton(false));
const sandbox = {
  console, parseFloat, parseInt, Number, Error,
  document: {
    documentElement: { lang: 'ar' },
    body: { dataset: { currency: 'ILS', sourceCurrency: 'ILS' } },
    addEventListener(type, fn) { if (type === 'DOMContentLoaded') domReady = fn; },
    getElementById() { return null; },
    querySelectorAll(sel) { return sel === '[data-add-cart]' ? buttons : []; },
  },
  localStorage: {
    getItem(k) { return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : null; },
    setItem(k, v) { storage[k] = String(v); },
  },
  window: { open() { calls.push('window.open'); } },
  SafeDOM: { clear() {}, elem() { return {}; } },
  StoreAPI: {
    getCartToken() { return storage.orion_cart_token || null; },
    async createCart() { calls.push('createCart'); return { cart: { cart_token: 'tok' } }; },
    setCartToken(t) { storage.orion_cart_token = t; calls.push('setCartToken'); },
    async getCart() { return { items: [] }; },
    async addItem(token, id, qty) { calls.push(`addItem:${id}:${qty}`); return {}; },
    async whatsappOrder() { calls.push('whatsappOrder'); return { url: 'https://wa.me/x' }; },
  },
};
vm.runInNewContext(source, sandbox);
(async () => {
  if (!domReady) throw new Error('cart.js did not register DOMContentLoaded');
  await domReady();
  await buttons[0].handler();
  const afterDisabled = calls.slice();
  const tokenAfterDisabled = Object.prototype.hasOwnProperty.call(storage, 'orion_cart_token');
  await buttons[1].handler();
  process.stdout.write(JSON.stringify({
    disabledCalls: afterDisabled,
    enabledCalls: calls.slice(afterDisabled.length),
    tokenAfterDisabled,
  }));
})().catch(e => {
  process.stderr.write(String((e && e.stack) || e));
  process.exitCode = 1;
});
"""


def test_cart_js_ignores_disabled_add_to_cart_button():
    node = shutil.which("node")
    assert node, "Node.js is required for the cart.js harness"
    result = subprocess.run(
        [node, "-e", NODE_HARNESS, str(CART_JS), "4242"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["disabledCalls"] == []
    assert report["tokenAfterDisabled"] is False
    assert report["enabledCalls"] == ["createCart", "setCartToken", "addItem:4242:1"]
