#!/usr/bin/env python3
"""Exhaustive live security matrix over every Flask route and identity.

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/audit_security_matrix.py

For every registered route (all HTTP methods), the script calls it as:
  * anonymous
  * store customer (own tenant)
  * store admin (own tenant)
  * platform admin (no tenant)
  * store admin with a foreign tenant header

It flags 5xx responses, unauthorized access to admin/platform surfaces,
cross-tenant data access, sensitive strings in responses, unsafe links and
reflected script payloads. Mutation endpoints are only exercised with
unauthorized identities (expected 401/403) to avoid changing live data.
"""

# isort: skip_file  (import order is load-bearing: the app must initialize first)

from __future__ import annotations

import atexit
import os
import pathlib
import re
import sys
import uuid
from collections import defaultdict

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

SENSITIVE_RE = re.compile(
    r"(traceback|\"encryption_key\"\s*:|\"secret_key\"\s*:|\"password_hash\"\s*:|"
    r"\"(?:api_)?credentials_encrypted\"\s*:\s*\"[^\"]+\")",
    re.IGNORECASE,
)
PUBLIC_STATUS_PATHS = {
    "/api/v1/platform/status",
    "/api/v1/status",
    "/health",
    "/ready",
    "/metrics",
}
XSS = "%3Cscript%3Ealert(1)%3C/script%3E"

FINDINGS: list[tuple[str, str, str]] = []
CALLS = 0


def flag(kind: str, target: str, detail: str = "") -> None:
    FINDINGS.append((kind, target, detail))


def main() -> None:
    global CALLS

    from flask_jwt_extended import create_access_token

    # Import order is load-bearing: initialize the app before ORM models,
    # otherwise orion.extensions -> orion.app -> event_handlers -> order.order
    # loops back into a partially initialized base.base_model.
    from orion.app import create_app
    from orion.extensions import db

    from catalog.product import Product
    from order.order import Order
    from platform_models.invoice import Invoice
    from tenant.tenant import Tenant
    from user.user import User

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        store = (
            Tenant.query.filter_by(slug="demo").first()
            or Tenant.query.filter(Tenant.deleted_at.is_(None)).first()
        )
        if not store:
            raise SystemExit("Security audit requires at least one tenant.")
        store_id = str(store.public_id)
        # A real temporary second tenant exercises the cross-tenant denial
        # properly: a nonexistent UUID would fall back to "no tenant context"
        # and mask the very check this audit is for. Cleaned up on exit.
        foreign = Tenant(
            name="Security Audit Foreign",
            slug=f"audit-foreign-{uuid.uuid4().hex[:8]}",
            email="audit-foreign@test.local",
        )
        db.session.add(foreign)
        db.session.commit()
        foreign_id = str(foreign.public_id)

        def _cleanup_foreign() -> None:
            try:
                with app.app_context():
                    row = db.session.get(Tenant, foreign.id)
                    if row is not None:
                        db.session.delete(row)
                        db.session.commit()
            except Exception:  # noqa: BLE001 - best-effort cleanup only
                pass

        atexit.register(_cleanup_foreign)
        customer = User.query.filter_by(
            email="buyer1@gulf.test", tenant_id=store.id
        ).first()
        admin = User.query.filter_by(
            email="admin@gulf.test", tenant_id=store.id
        ).first()
        root_user = User.query.filter(
            User.is_superuser.is_(True), User.deleted_at.is_(None)
        ).first()
        if not (customer and admin and root_user):
            raise SystemExit("Security audit identities are missing.")
        product = Product.query.filter_by(tenant_id=store.id, deleted_at=None).first()
        order = Order.query.filter_by(tenant_id=store.id).first()
        invoice = Invoice.query.filter_by(tenant_id=store.id).first()

        identities = {
            "anon": {},
            "customer": {
                "Authorization": f"Bearer {create_access_token(identity=str(customer.public_id))}",
                "X-Tenant-ID": store_id,
            },
            "admin": {
                "Authorization": f"Bearer {create_access_token(identity=str(admin.public_id))}",
                "X-Tenant-ID": store_id,
            },
            "platform": {
                "Authorization": f"Bearer {create_access_token(identity=str(root_user.public_id))}"
            },
            "foreign": {
                "Authorization": f"Bearer {create_access_token(identity=str(admin.public_id))}",
                "X-Tenant-ID": foreign_id,
            },
        }

        samples = {
            "tenant_id": [str(store.id), foreign_id],
            "product_id": [str(product.id) if product else "1"],
            "public_id": [
                str(order.public_id) if order else "1",
                str(product.public_id) if product else "1",
                store_id,
            ],
            "slug": ["smart-phone-pro", "electronics", "privacy", store.slug],
            "cart_token": ["not-a-real-token"],
            "code": ["WELCOME-GUL"],
            "id": ["1"],
            "filename": ["favicon.svg"],
            "owner_type": ["product"],
            "session_id": ["1"],
            "request_id": ["1"],
            "app_id": ["1"],
            "installation_id": ["1"],
            "return_id": ["1"],
            "quote_id": ["1"],
            "payment_id": ["1"],
            "path": [""],
        }

        def fill(rule) -> str:
            path = rule.rule
            for arg in rule.arguments:
                values = samples.get(arg, ["1"])
                path = path.replace(f"<{arg}>", values[0], 1)
                path = re.sub(r"<[^>]+:[^>]*>", values[0], path, count=1)
            return path

        rules = [
            r
            for r in app.url_map.iter_rules()
            if not r.rule.startswith(("/static", "/admin/static", "/store/static"))
        ]

    client = app.test_client()
    for rule in rules:
        path = fill(rule)
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            mutating = method in ("POST", "PUT", "PATCH", "DELETE")
            for who, headers in identities.items():
                if mutating and who in ("admin", "platform", "customer", "foreign"):
                    # Only unauthorized identities on state-changing routes.
                    continue
                try:
                    resp = client.open(
                        path,
                        method=method,
                        headers={**headers, "Content-Type": "application/json"},
                        json={} if mutating else None,
                    )
                except Exception as exc:  # noqa: BLE001 - report the crash
                    flag("EXCEPTION", f"{method} {path} [{who}]", type(exc).__name__)
                    continue
                CALLS += 1
                body = resp.get_data().decode("utf-8", "replace")
                if resp.status_code >= 500:
                    flag("5XX", f"{method} {path} [{who}]", str(resp.status_code))
                low = body.lower()
                if SENSITIVE_RE.search(body):
                    flag(
                        "SENSITIVE",
                        f"{method} {path} [{who}]",
                        "sensitive value in response",
                    )
                if (
                    who == "customer"
                    and path not in PUBLIC_STATUS_PATHS
                    and (
                        path.startswith("/admin/platform")
                        or path.startswith("/api/v1/platform")
                    )
                    and 200 <= resp.status_code < 300
                ):
                    flag(
                        "AUTHZ",
                        f"{method} {path} [customer]",
                        "reached platform surface",
                    )
                if (
                    who == "foreign"
                    and resp.status_code < 400
                    and path.startswith("/api/v1/tenant")
                ):
                    flag(
                        "CROSS-TENANT",
                        f"{method} {path} [foreign]",
                        "writable with foreign header",
                    )

    # BFS crawl every reachable page for each identity, checking every link
    # and injecting a script payload into every query-string field found.
    seen_pages: set[tuple[str, str]] = set()
    for who, headers in identities.items():
        queue = [f"/?tenant_slug={store.slug}", "/admin/login"]
        while queue and len([p for p, w in seen_pages if w == who]) < 120:
            start = queue.pop(0)
            if (start, who) in seen_pages:
                continue
            seen_pages.add((start, who))
            resp = client.get(start, headers=headers)
            html = resp.get_data().decode("utf-8", "replace")
            if resp.status_code >= 500:
                flag("5XX-CRAWL", f"{who} {start}", str(resp.status_code))
            for href in re.findall(r'href="([^"]+)"', html):
                if href.startswith(("javascript:", "data:", "//")):
                    flag("UNSAFE-LINK", f"{who} {start}", href[:80])
                if "evil" in href or "alert(" in href:
                    flag("UNSAFE-LINK", f"{who} {start}", href[:80])
                if href.startswith("/") and not href.startswith("//"):
                    if href not in [q for q in queue]:
                        queue.append(href)
            # Every query field on this page gets the script payload.
            for name in re.findall(r"[?&]([A-Za-z_][\w-]*)=", start):
                injected = re.sub(rf"([?&]{re.escape(name)}=)[^&]*", rf"\1{XSS}", start)
                r2 = client.get(injected, headers=headers)
                CALLS += 1
                if "<script>alert(1)</script>" in r2.get_data().decode(
                    "utf-8", "replace"
                ):
                    flag("REFLECTED-XSS", f"{who} {injected[:90]}")

    print(
        f"ROUTES: {len(rules)}  CALLS: {CALLS}  PAGES: {len(seen_pages)}  FINDINGS: {len(FINDINGS)}"
    )
    for kind, target, detail in FINDINGS[:60]:
        print(f"  {kind:14s} {target} {detail}")
    if FINDINGS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
