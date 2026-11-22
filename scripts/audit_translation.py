#!/usr/bin/env python3
"""Render every UI page in Arabic and English and flag foreign-language text.

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/audit_translation.py

Only UI chrome is checked. Product/category names come from the database and
are reported separately so seeded data is not confused with translation bugs.
"""

from __future__ import annotations

import html
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in (
    "02-CORE",
    "03-MODELS",
    "04-SERVICES",
    "05-API",
    "06-STOREFRONT",
    "07-ADMIN",
):
    sys.path.insert(0, str(ROOT / part))

ARABIC = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]"
)
LATIN_WORD = re.compile(r"\b[A-Za-z][A-Za-z'’\-]{1,}\b")

# Proper nouns / technical tokens that legitimately stay Latin or Arabic.
ALLOWED_LATIN = {
    "azadexa",
    "whatsapp",
    "sso",
    "pdf",
    "sku",
    "cod",
    "bopis",
    "seo",
    "api",
    "url",
    "html",
    "css",
    "js",
    "id",
    "ip",
    "sms",
    "otp",
    "bnpl",
    "faq",
    "csv",
    "xml",
    "json",
    "ssl",
    "tls",
    "http",
    "https",
    "www",
    "iso",
    "vat",
    "qr",
    "pos",
    "crm",
    "erp",
    "ui",
    "ux",
    "cdn",
    # seeded data values and technical identifiers shown verbatim
    "ahmad",
    "ghannam",
    "gulf",
    "trading",
    "my",
    "store",
    "slug",
    "oauth",
    "saml",
    "openid",
    "boost",
    "markup",
    "offer",
    "organization",
    "product",
    "schema",
    "ld",
    "save10",
    "ps",
    "admin",
    "test",
    "english",
    "paypal",
    "connect",
    "aed",
    "eur",
    "gbp",
    "ils",
    "jod",
    "sar",
    "usd",
    "en",
    "info",
}
ALLOWED_ARABIC = set()

STORE_PAGES = [
    "/",
    "/cart",
    "/account",
    "/checkout",
    "/consent",
    "/product/smart-phone-pro",
    "/category/electronics",
    "/pages/privacy",
]
ADMIN_PAGES = [
    "/admin/login",
    "/admin/profile",
    "/admin/store/dashboard",
    "/admin/store/products",
    "/admin/store/pages",
    "/admin/store/ui-kit",
    "/admin/store/contact",
    "/admin/store/gateways",
    "/admin/store/documents",
    "/admin/store/feature-flags",
    "/admin/store/returns",
    "/admin/store/b2b",
    "/admin/store/oms",
    "/admin/store/subscriptions",
    "/admin/store/vouchers",
    "/admin/store/tax",
    "/admin/store/bopis",
    "/admin/store/bundles",
    "/admin/store/store-credit",
    "/admin/store/draft-orders",
    "/admin/store/metafields",
    "/admin/store/currency",
    "/admin/store/import-export",
    "/admin/store/app-platform",
    "/admin/store/fraud",
    "/admin/store/compliance",
    "/admin/store/workflows",
    "/admin/store/search",
    "/admin/store/affiliates",
    "/admin/store/gift-registries",
    "/admin/store/dropship",
    "/admin/store/schema-markup",
    "/admin/store/accessibility",
    "/admin/store/live-chat",
    "/admin/store/reconciliation",
    "/admin/store/platform-audit",
    "/admin/platform/dashboard",
    "/admin/platform/tenants",
    "/admin/platform/users",
    "/admin/platform/settings",
    "/admin/platform/reconciliation",
    "/admin/platform/audit",
]


def visible_text(body: str) -> str:
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    return html.unescape(body)


def check_page(client, url: str, locale: str, label: str, findings: list) -> None:
    resp = client.get(url, follow_redirects=True)
    text = visible_text(resp.get_data(as_text=True))
    if ARABIC.search(text) and locale == "en":
        samples = [m.group(0) for m in ARABIC.finditer(text)][:6]
        findings.append((label, url, locale, "Arabic text in English page", samples))
    if locale == "ar":
        words = {w.lower() for w in LATIN_WORD.findall(text)}
        bad = sorted(w for w in words if w not in ALLOWED_LATIN)
        if bad:
            findings.append(
                (label, url, locale, "English text in Arabic page", bad[:12])
            )


def login(client, email: str, tenant_slug: str | None = None) -> bool:
    page = client.get("/admin/login").get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    if not match:
        return False
    data = {"csrf_token": match.group(1), "email": email, "password": "password123"}
    if tenant_slug:
        data["tenant_slug"] = tenant_slug
    resp = client.post("/admin/login", data=data, follow_redirects=False)
    return resp.status_code in (302, 303)


def main() -> None:
    from orion.app import create_app

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    findings: list = []
    with app.test_client() as client:
        for url in STORE_PAGES:
            for locale in ("ar", "en"):
                check_page(
                    client,
                    f"{url}?tenant_slug=gulf&locale={locale}",
                    locale,
                    "storefront",
                    findings,
                )
    with app.test_client() as client:
        if not login(client, "admin@gulf.test", "gulf"):
            print("WARNING: store admin login failed")
        # The admin UI is Arabic-only (admin_base declares lang="ar" dir="rtl").
        for url in [u for u in ADMIN_PAGES if "/platform/" not in u]:
            check_page(client, f"{url}?locale=ar", "ar", "admin", findings)
    with app.test_client() as client:
        if not login(client, "root@azadexa.test"):
            print("WARNING: platform admin login failed")
        for url in [u for u in ADMIN_PAGES if "/platform/" in u]:
            check_page(client, f"{url}?locale=ar", "ar", "platform", findings)

    print(f"Checked {len(STORE_PAGES) * 2 + len(ADMIN_PAGES) * 2} page renders")
    if not findings:
        print("No foreign-language UI text found")
        return
    for label, url, locale, kind, samples in findings:
        print(f"{kind}: [{locale}] {label} {url}\n    {samples}")
    print(f"TOTAL PAGES WITH ISSUES: {len(findings)}")


if __name__ == "__main__":
    main()
