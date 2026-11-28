"""Round-12 regression: share captions wrap URLs in FSI/PDI bidi isolates."""

from __future__ import annotations

import codecs
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService

ROOT = Path(__file__).resolve().parents[2]
SHARE_JS = ROOT / "06-STOREFRONT/themes/default/static/js/store_share.js"

FSI = "\u2068"
PDI = "\u2069"
FSI_ENC = "%E2%81%A8"
PDI_ENC = "%E2%81%A9"

SHARE_FILES = (
    "06-STOREFRONT/themes/default/templates/components/header.html",
    "06-STOREFRONT/themes/default/templates/product.html",
    "06-STOREFRONT/themes/default/templates/components/product_card.html",
    "06-STOREFRONT/themes/default/static/js/store_share.js",
)


class _Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _find(html, tag=None, **matching):
    parser = _Tags()
    parser.feed(html)
    return [
        attrs
        for name, attrs in parser.tags
        if (tag is None or name == tag)
        and all(attrs.get(key) == value for key, value in matching.items())
    ]


def _wa_share_links(html):
    return [
        a
        for a in _find(html, "a")
        if (a.get("href") or "").startswith("https://wa.me/?text=")
    ]


def _caption(href, *, param):
    return unquote(parse_qs(urlparse(href).query)[param][0])


def _wrapped(caption):
    assert caption.count(FSI) == 1, caption
    assert caption.count(PDI) == 1, caption
    assert caption.index(FSI) < caption.index(PDI), caption
    return caption[caption.index(FSI) + 1 : caption.index(PDI)]


def _assert_isolated(caption, url_suffix):
    url = _wrapped(caption)
    assert url.startswith(("http://", "https://")), caption
    assert url.endswith(url_suffix), caption
    assert caption.endswith(PDI), caption


@pytest.fixture(autouse=True)
def _guard_not_live_db(database_url: str) -> None:
    url = database_url.lower()
    assert ":memory:" in url or "test" in url, f"non-test DB: {database_url!r}"


@pytest.fixture
def bidi_store():
    tenant = TenantService().create_tenant(
        name="Bidi Store", slug="bidi-store", email="bidi@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Bidi Widget",
        slug="bidi-widget",
        price="9.99",
        quantity=3,
        is_published=True,
    )
    return SimpleNamespace(
        tenant=tenant, product=product, headers=tenant_headers(tenant.slug)
    )


@pytest.mark.parametrize("rel", SHARE_FILES)
def test_share_surfaces_declare_fsi_pdi(rel):
    source = (ROOT / rel).read_text(encoding="utf-8")
    assert r"\u2068" in source, rel
    assert r"\u2069" in source, rel


def test_store_share_js_composes_caption_with_fsi_pdi():
    source = SHARE_JS.read_text(encoding="utf-8")
    assert r'const FSI = "\u2068", PDI = "\u2069";' in source
    assert r'const text = title + " — " + FSI + url + PDI;' in source
    assert codecs.decode(r"\u2068", "unicode_escape") == FSI
    assert codecs.decode(r"\u2069", "unicode_escape") == PDI


def test_header_store_share_caption_is_isolated(client, app, bidi_store):
    resp = client.get("/", headers=bidi_store.headers)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    wa = _find(html, "a", **{"data-share-target": "whatsapp"})
    mail = _find(html, "a", **{"data-share-target": "email"})
    assert len(wa) == 1 and len(mail) == 1
    _assert_isolated(_caption(wa[0]["href"], param="text"), "/s/bidi-store/")
    _assert_isolated(_caption(mail[0]["href"], param="body"), "/s/bidi-store/")
    assert FSI_ENC in html and PDI_ENC in html


def test_product_share_caption_is_isolated(client, app, bidi_store):
    resp = client.get("/product/bidi-widget", headers=bidi_store.headers)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    links = _wa_share_links(html)
    assert len(links) == 2
    captions = [_caption(a["href"], param="text") for a in links]
    for caption in captions:
        _wrapped(caption)
    assert any(_wrapped(c).endswith("/product/bidi-widget") for c in captions)
    assert FSI_ENC in html and PDI_ENC in html


def test_product_card_share_caption_is_isolated(client, app, bidi_store):
    resp = client.get("/", headers=bidi_store.headers)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    card_links = [a for a in _wa_share_links(html) if "data-share-target" not in a]
    assert len(card_links) >= 1
    for a in card_links:
        _assert_isolated(_caption(a["href"], param="text"), "/product/bidi-widget")
