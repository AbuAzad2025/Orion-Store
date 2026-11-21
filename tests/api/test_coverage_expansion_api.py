"""Coverage expansion for the low-coverage v1 API route modules.

All tests are integration-style: they go through the Flask test client, hit real
routes and services, and persist to the real PostgreSQL test database. No CRUD
or service behaviour is mocked.
"""

from __future__ import annotations

import base64
import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.utils import utc_now
from discount.voucher import Voucher
from orion.extensions import db
from order.order import Order
from payment.payment import Payment
from platform_models.impersonation_session import ImpersonationSession
from tenant_svc.tenant_service import TenantService
from user.user import User

# The registration-level url_prefix overrides the blueprint-level one, so the
# impersonation routes are mounted at /api/v1/{start,end,status}.
IMP_BASE = "/api/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_ctx(app):
    tenant = TenantService().create_tenant(
        name="Cov Tenant", slug="cov-tenant", email="cov@tenant.test"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@cov.test",
        password="password123",
        is_admin=True,
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="buyer@cov.test",
        password="password123",
        is_admin=False,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Cov Product",
        slug="cov-product",
        price="25.00",
        quantity=20,
        is_published=True,
    )
    return SimpleNamespace(
        tenant=tenant,
        admin=admin,
        customer=customer,
        product=product,
        headers=auth_headers(admin, app=app, tenant_id=tenant.slug),
        store_headers=tenant_headers(tenant.slug),
        customer_headers=auth_headers(customer, app=app, tenant_id=tenant.slug),
    )


@pytest.fixture
def imp_ctx(app):
    tenant = TenantService().create_tenant(
        name="Imp Cov", slug="imp-cov", email="imp@cov.test"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="impadmin@cov.test",
        password="password123",
        is_admin=True,
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="impbuyer@cov.test",
        password="password123",
        is_admin=False,
    )
    su = AuthService().register_super_admin(
        email="impsu@cov.test", password="password123"
    )
    return SimpleNamespace(
        tenant=tenant,
        admin=admin,
        customer=customer,
        su=su,
        headers=auth_headers(su, app=app),
    )


def _make_order(app, tenant_id, *, total="150.00", number=None):
    with app.app_context():
        order = Order(
            tenant_id=tenant_id,
            user_id=None,
            order_number=number or f"COV-{uuid.uuid4().hex[:10]}",
            status="pending",
            payment_status="pending",
            fulfillment_status="unfulfilled",
            customer_email="buyer@cov.test",
            customer_first_name="Coverage",
            customer_last_name="Buyer",
            is_guest=True,
            shipping_address={},
            subtotal=total,
            tax_amount="0",
            shipping_cost="0",
            discount_amount="0",
            total=total,
        )
        db.session.add(order)
        db.session.commit()
        return order.id


def _make_payment(app, tenant_id, order_id, amount="150.00"):
    with app.app_context():
        payment = Payment(
            tenant_id=tenant_id,
            order_id=order_id,
            amount=Decimal(amount),
            currency="ILS",
            payment_method="card",
            payment_provider="test",
            status="paid",
        )
        db.session.add(payment)
        db.session.commit()
        return payment.id


def _clear_jwt_cookies(client):
    """Impersonation responses set cookies that outrank explicit Bearer headers."""
    client.flask_client.delete_cookie("access_token_cookie")
    client.flask_client.delete_cookie("refresh_token_cookie")


# ---------------------------------------------------------------------------
# tenants.py
# ---------------------------------------------------------------------------


def test_tenants_full_crud_pagination_and_errors(client, platform_admin_headers):
    headers = platform_admin_headers
    assert client.get("/api/v1/tenants/").status_code == 401
    assert (
        client.get(
            "/api/v1/tenants/?page=abc&per_page=abc", headers=headers
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/v1/tenants/", headers=headers, json={"name": "NoSlug"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/tenants/",
            headers=headers,
            json={
                "name": "Bad Status",
                "slug": "bad-status",
                "email": "bad@cov.test",
                "status": "not-a-status",
            },
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/tenants/",
        headers=headers,
        json={
            "name": "Cov API Store",
            "slug": "cov-api-store",
            "email": "covapi@cov.test",
            "domain": "cov-api.example",
            "status": "active",
            "admin_email": "owner@covapi.test",
            "admin_password": "password123",
        },
    )
    assert created.status_code == 201
    tenant = created.get_json()["tenant"]
    tenant_id = tenant["id"]
    assert tenant["name"] == "Cov API Store"
    assert tenant["status"] == "active"
    assert tenant["domain"] == "cov-api.example"

    duplicate = client.post(
        "/api/v1/tenants/",
        headers=headers,
        json={"name": "Dup", "slug": "cov-api-store", "email": "dup@cov.test"},
    )
    assert duplicate.status_code == 400

    assert (
        client.get(f"/api/v1/tenants/{tenant_id}", headers=headers).status_code == 200
    )
    assert client.get("/api/v1/tenants/999999", headers=headers).status_code == 404
    assert client.get(f"/api/v1/tenants/{tenant_id}").status_code == 401
    assert (
        client.put(f"/api/v1/tenants/{tenant_id}", json={"name": "x"}).status_code
        == 401
    )
    assert client.delete(f"/api/v1/tenants/{tenant_id}").status_code == 401

    me = client.get("/api/v1/tenants/me", headers=tenant_headers("cov-api-store"))
    assert me.status_code == 200
    assert me.get_json()["tenant"]["slug"] == "cov-api-store"
    assert client.get("/api/v1/tenants/me", headers=headers).status_code == 404

    updated = client.put(
        f"/api/v1/tenants/{tenant_id}",
        headers=headers,
        json={
            "name": "Renamed Store",
            "email": "renamed@cov.test",
            "domain": "renamed.example",
            "status": "suspended",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["tenant"]["name"] == "Renamed Store"
    assert (
        client.put(
            "/api/v1/tenants/999999", headers=headers, json={"name": "x"}
        ).status_code
        == 404
    )

    # A non-dict JSON body raises before any DB write, exercising the generic
    # 400 handler without poisoning the request's SQLAlchemy session.
    assert (
        client.put(
            f"/api/v1/tenants/{tenant_id}", headers=headers, json=["name"]
        ).status_code
        == 400
    )

    assert (
        client.delete(f"/api/v1/tenants/{tenant_id}", headers=headers).status_code
        == 200
    )
    assert (
        client.delete(f"/api/v1/tenants/{tenant_id}", headers=headers).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/tenants/{tenant_id}", headers=headers).status_code == 404
    )


# ---------------------------------------------------------------------------
# vouchers.py
# ---------------------------------------------------------------------------


def test_vouchers_list_create_apply_delete_and_errors(client, tenant_ctx):
    headers = tenant_ctx.headers
    store = tenant_ctx.store_headers
    assert client.get("/api/v1/vouchers/").status_code == 401
    assert (
        client.post(
            "/api/v1/vouchers/", json={"code": "NOAUTH", "value": "1"}
        ).status_code
        == 401
    )
    assert client.get("/api/v1/vouchers/", headers=headers).status_code == 200
    assert (
        client.post(
            "/api/v1/vouchers/", headers=headers, json={"code": "NOVALUE"}
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={
            "code": "save10",
            "name": "Save Ten",
            "type": "percentage",
            "value": "10",
            "max_discount_amount": "5",
            "is_free_shipping": True,
        },
    )
    assert created.status_code == 201
    assert created.get_json()["voucher"]["code"] == "SAVE10"
    assert (
        len(client.get("/api/v1/vouchers/", headers=headers).get_json()["vouchers"])
        == 1
    )

    validated = client.get(
        "/api/v1/vouchers/SAVE10/validate?subtotal=100", headers=store
    )
    assert validated.status_code == 200
    assert validated.get_json()["voucher"]["discount_amount"] == "5.00"
    assert validated.get_json()["voucher"]["is_free_shipping"] is True

    applied = client.post(
        "/api/v1/vouchers/save10/apply", headers=store, json={"subtotal": "100"}
    )
    assert applied.status_code == 200
    assert applied.get_json()["applied"]["discount_amount"] == "5.00"

    assert (
        client.get(
            "/api/v1/vouchers/MISSING/validate?subtotal=100", headers=store
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/vouchers/MISSING/apply", headers=store, json={"subtotal": "100"}
        ).status_code
        == 404
    )
    assert (
        client.get("/api/v1/vouchers/SAVE10/validate?subtotal=100").status_code == 404
    )

    deleted = client.delete("/api/v1/vouchers/SAVE10", headers=headers)
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted"] is True
    assert client.delete("/api/v1/vouchers/SAVE10", headers=headers).status_code == 404
    assert (
        client.get(
            "/api/v1/vouchers/SAVE10/validate?subtotal=100", headers=store
        ).status_code
        == 404
    )


def test_vouchers_validation_error_branches(client, tenant_ctx, app):
    headers = tenant_ctx.headers
    store = tenant_ctx.store_headers
    tenant_id = tenant_ctx.tenant.id

    fixed = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={"code": "FIX10", "name": "Fixed", "type": "fixed_amount", "value": "10"},
    )
    assert fixed.status_code == 201
    fixed_res = client.get(
        "/api/v1/vouchers/FIX10/validate?subtotal=100", headers=store
    )
    assert fixed_res.get_json()["voucher"]["discount_amount"] == "10.00"

    minimum = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={
            "code": "MIN200",
            "name": "Minimum",
            "value": "10",
            "min_order_value": "200",
        },
    )
    assert minimum.status_code == 201
    assert (
        client.get(
            "/api/v1/vouchers/MIN200/validate?subtotal=100", headers=store
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/vouchers/MIN200/validate?subtotal=250", headers=store
        ).status_code
        == 200
    )

    limited = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={"code": "LIMIT1", "name": "Limited", "value": "10", "usage_limit": 1},
    )
    assert limited.status_code == 201
    with app.app_context():
        voucher = Voucher.query.filter_by(tenant_id=tenant_id, code="LIMIT1").one()
        voucher.usage_count = 1
        db.session.commit()
    assert (
        client.get(
            "/api/v1/vouchers/LIMIT1/validate?subtotal=100", headers=store
        ).status_code
        == 400
    )

    dated = client.post(
        "/api/v1/vouchers/",
        headers=headers,
        json={"code": "DATED", "name": "Dated", "value": "10"},
    )
    assert dated.status_code == 201
    with app.app_context():
        voucher = Voucher.query.filter_by(tenant_id=tenant_id, code="DATED").one()
        voucher.start_date = utc_now() + timedelta(days=1)
        db.session.commit()
    assert (
        client.get(
            "/api/v1/vouchers/DATED/validate?subtotal=100", headers=store
        ).status_code
        == 400
    )
    with app.app_context():
        voucher = Voucher.query.filter_by(tenant_id=tenant_id, code="DATED").one()
        voucher.start_date = None
        voucher.end_date = utc_now() - timedelta(days=1)
        db.session.commit()
    assert (
        client.get(
            "/api/v1/vouchers/DATED/validate?subtotal=100", headers=store
        ).status_code
        == 400
    )


# ---------------------------------------------------------------------------
# impersonation.py
# ---------------------------------------------------------------------------


def test_impersonation_start_validation_errors(client, imp_ctx, app):
    headers = imp_ctx.headers
    assert (
        client.post(
            f"{IMP_BASE}/start", json={"target_user_id": imp_ctx.admin.id}
        ).status_code
        == 401
    )
    assert client.post(f"{IMP_BASE}/start", headers=headers, json={}).status_code == 400
    assert (
        client.post(
            f"{IMP_BASE}/start", headers=headers, json={"target_user_id": "x"}
        ).status_code
        == 400
    )
    for bad_duration in (0, 5, "2"):
        assert (
            client.post(
                f"{IMP_BASE}/start",
                headers=headers,
                json={
                    "target_user_id": imp_ctx.admin.id,
                    "duration_hours": bad_duration,
                },
            ).status_code
            == 400
        )
    assert (
        client.post(
            f"{IMP_BASE}/start", headers=headers, json={"target_user_id": 999999}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{IMP_BASE}/start", headers=headers, json={"target_user_id": imp_ctx.su.id}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{IMP_BASE}/start",
            headers=headers,
            json={"target_user_id": imp_ctx.customer.id},
        ).status_code
        == 403
    )

    with app.app_context():
        orphan = User(
            email="orphan@cov.test",
            password_hash="unused",
            tenant_id=None,
            is_admin=True,
            is_superuser=False,
            is_customer=False,
            is_active=True,
        )
        db.session.add(orphan)
        db.session.commit()
        orphan_id = orphan.id
    assert (
        client.post(
            f"{IMP_BASE}/start", headers=headers, json={"target_user_id": orphan_id}
        ).status_code
        == 400
    )

    tenant_admin_headers = auth_headers(
        imp_ctx.admin, app=app, tenant_id=imp_ctx.tenant.slug
    )
    assert (
        client.post(
            f"{IMP_BASE}/start",
            headers=tenant_admin_headers,
            json={"target_user_id": imp_ctx.admin.id},
        ).status_code
        == 401
    )


def test_impersonation_start_status_end_with_claims(client, imp_ctx, app):
    started = client.post(
        f"{IMP_BASE}/start",
        headers=imp_ctx.headers,
        json={"target_user_id": imp_ctx.admin.id, "duration_hours": 2},
    )
    assert started.status_code == 200
    body = started.get_json()
    assert body["session"]["target_user_id"] == imp_ctx.admin.id
    assert body["target_user"]["email"] == imp_ctx.admin.email

    # The start response sets impersonation cookies; middleware validates them.
    status = client.get(f"{IMP_BASE}/status")
    assert status.status_code == 200
    assert status.get_json()["active"] is True
    assert status.get_json()["session"]["target_user_id"] == imp_ctx.admin.id

    ended = client.post(f"{IMP_BASE}/end")
    assert ended.status_code == 200
    assert ended.get_json()["message"] == "Impersonation ended"
    with app.app_context():
        session = ImpersonationSession.query.filter_by(
            impersonator_user_id=imp_ctx.su.id, target_user_id=imp_ctx.admin.id
        ).first()
        assert session is not None
        assert session.revoked is True
        assert session.ended_at is not None


def test_impersonation_status_end_without_session_and_unauthorized(
    client, imp_ctx, app
):
    status = client.get(f"{IMP_BASE}/status", headers=imp_ctx.headers)
    assert status.status_code == 200
    assert status.get_json() == {"active": False, "session": None}

    ended = client.post(f"{IMP_BASE}/end", headers=imp_ctx.headers)
    assert ended.status_code == 200
    assert ended.get_json()["active"] is False
    assert ended.get_json()["session"] is None

    customer_headers = auth_headers(
        imp_ctx.customer, app=app, tenant_id=imp_ctx.tenant.slug
    )
    assert client.get(f"{IMP_BASE}/status", headers=customer_headers).status_code == 200
    assert client.post(f"{IMP_BASE}/end", headers=customer_headers).status_code == 401


def test_impersonation_duplicate_start_conflict(client, imp_ctx):
    first = client.post(
        f"{IMP_BASE}/start",
        headers=imp_ctx.headers,
        json={"target_user_id": imp_ctx.admin.id},
    )
    assert first.status_code == 200
    _clear_jwt_cookies(client)
    second = client.post(
        f"{IMP_BASE}/start",
        headers=imp_ctx.headers,
        json={"target_user_id": imp_ctx.admin.id},
    )
    assert second.status_code == 409


def test_impersonation_platform_admin_active_session_and_claim_edges(
    client, imp_ctx, app
):
    from flask_jwt_extended import create_access_token

    started = client.post(
        f"{IMP_BASE}/start",
        headers=imp_ctx.headers,
        json={"target_user_id": imp_ctx.admin.id},
    )
    assert started.status_code == 200
    _clear_jwt_cookies(client)

    # Without impersonation claims, a platform admin can see and end the session.
    status = client.get(f"{IMP_BASE}/status", headers=imp_ctx.headers)
    assert status.get_json()["active"] is True
    ended = client.post(f"{IMP_BASE}/end", headers=imp_ctx.headers)
    assert ended.status_code == 200
    assert ended.get_json()["message"] == "Impersonation ended"

    # Claims without a matching session are simply reported as inactive.
    def _claim_headers(impersonator_id, target_id):
        token = create_access_token(
            identity=str(imp_ctx.su.public_id),
            additional_claims={
                "is_superuser": True,
                "tenant_id": None,
                "impersonation": {
                    "impersonator_user_id": impersonator_id,
                    "target_user_id": target_id,
                },
            },
        )
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    _clear_jwt_cookies(client)
    no_session = client.get(
        f"{IMP_BASE}/status", headers=_claim_headers(999999, 999999)
    )
    assert no_session.status_code == 200
    assert no_session.get_json() == {"active": False, "session": None}

    # A live session whose impersonator is not an active superadmin cannot be
    # restored to a platform-admin identity.
    with app.app_context():
        session = ImpersonationSession(
            impersonator_user_id=imp_ctx.admin.id,
            target_user_id=imp_ctx.admin.id,
            tenant_id=imp_ctx.tenant.id,
            started_at=utc_now(),
            expires_at=utc_now() + timedelta(hours=1),
        )
        db.session.add(session)
        db.session.commit()
    _clear_jwt_cookies(client)
    no_impersonator = client.post(
        f"{IMP_BASE}/end",
        headers=_claim_headers(imp_ctx.admin.id, imp_ctx.admin.id),
    )
    assert no_impersonator.status_code == 404

    # The same session is now revoked, so a repeat request reports it inactive.
    inactive = client.post(
        f"{IMP_BASE}/end",
        headers=_claim_headers(imp_ctx.admin.id, imp_ctx.admin.id),
    )
    assert inactive.status_code == 200
    assert inactive.get_json()["reason"] == "Session expired or revoked"


# ---------------------------------------------------------------------------
# currency_api.py
# ---------------------------------------------------------------------------


def test_currency_rates_conversion_branches(client, platform_admin_headers):
    headers = platform_admin_headers
    assert client.get("/api/v1/currency/rates").status_code == 401
    assert client.get("/api/v1/currency/rates", headers=headers).status_code == 200
    assert (
        client.post(
            "/api/v1/currency/rates",
            headers=headers,
            json={"to_currency": "EUR", "rate": "1"},
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/currency/rates",
        headers=headers,
        json={
            "from_currency": "usd",
            "to_currency": "eur",
            "rate": "0.85",
            "source": "manual-feed",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["rate"]["from_currency"] == "USD"
    assert created.get_json()["rate"]["source"] == "manual-feed"
    assert client.get("/api/v1/currency/rates", headers=headers).get_json()["rates"]

    assert (
        client.post(
            "/api/v1/currency/rates",
            json={"from_currency": "USD", "to_currency": "EUR", "rate": "1"},
        ).status_code
        == 401
    )

    same = client.get("/api/v1/currency/convert?amount=100&from=USD&to=USD")
    assert same.status_code == 200
    assert same.get_json()["result"] == "100"

    direct = client.get("/api/v1/currency/convert?amount=100&from=USD&to=EUR")
    assert direct.get_json()["result"] == "85.00"

    assert (
        client.post(
            "/api/v1/currency/rates",
            headers=headers,
            json={"from_currency": "GBP", "to_currency": "ILS", "rate": "5"},
        ).status_code
        == 201
    )
    inverse = client.get("/api/v1/currency/convert?amount=100&from=ILS&to=GBP")
    assert inverse.get_json()["result"] == "20.00"

    no_rate = client.get("/api/v1/currency/convert?amount=100&from=AAA&to=BBB")
    assert no_rate.get_json()["result"] == "100"

    invalid = client.get("/api/v1/currency/convert?amount=not-a-number")
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "Invalid request."


# ---------------------------------------------------------------------------
# audit_api.py
# ---------------------------------------------------------------------------


def test_audit_reports_and_logs(client, platform_admin_headers):
    headers = platform_admin_headers
    assert client.get("/api/v1/audit/reports").status_code == 401
    assert (
        client.post(
            "/api/v1/audit/reports", json={"report_type": "monthly"}
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/audit/reports", headers=headers).get_json()["reports"] == []
    )
    assert (
        client.post(
            "/api/v1/audit/reports", headers=headers, json={"summary": {}}
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/audit/reports",
        headers=headers,
        json={
            "report_type": "monthly",
            "summary": {"total": 1},
            "details": [{"item": 1}],
        },
    )
    assert created.status_code == 201
    assert created.get_json()["report"]["report_type"] == "monthly"
    assert (
        created.get_json()["report"]["generated_by"]
        == User.query.filter_by(email="owner@azadexa.com").first().id
    )
    defaulted = client.post(
        "/api/v1/audit/reports", headers=headers, json={"report_type": "weekly"}
    )
    assert defaulted.status_code == 201
    assert (
        len(client.get("/api/v1/audit/reports", headers=headers).get_json()["reports"])
        == 2
    )

    assert client.get("/api/v1/audit/logs").status_code == 401
    assert client.get("/api/v1/audit/logs", headers=headers).get_json()["logs"] == []
    assert client.get("/api/v1/audit/logs?limit=1", headers=headers).status_code == 200

    logged = client.post(
        "/api/v1/audit/logs",
        headers=headers,
        json={
            "action": "user.login",
            "target_type": "user",
            "target_id": 1,
            "details": {"ip": "1.2.3.4"},
        },
    )
    assert logged.status_code == 201
    assert logged.get_json()["log"]["action"] == "user.login"
    assert (
        len(
            client.get("/api/v1/audit/logs?limit=1", headers=headers).get_json()["logs"]
        )
        == 1
    )

    assert (
        client.post(
            "/api/v1/audit/logs", headers=headers, json={"details": {}}
        ).status_code
        == 400
    )
    assert client.post("/api/v1/audit/logs", json={"action": "x"}).status_code == 401


# ---------------------------------------------------------------------------
# schema_markup.py
# ---------------------------------------------------------------------------


def test_schema_markup_crud_and_errors(client, tenant_ctx):
    headers = tenant_ctx.headers
    product_id = tenant_ctx.product.id
    assert client.get("/api/v1/schema-markup").status_code == 401
    assert (
        client.post(
            "/api/v1/schema-markup", json={"product_id": product_id}
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/schema-markup", headers=headers).get_json()["markups"] == []
    )
    assert (
        client.post(
            "/api/v1/schema-markup", headers=headers, json={"schema_type": "Product"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/schema-markup", headers=headers, json={"product_id": "abc"}
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/schema-markup",
        headers=headers,
        json={
            "product_id": product_id,
            "schema_type": "Product",
            "json_ld": {"name": "Cov"},
        },
    )
    assert created.status_code == 201
    assert created.get_json()["markup"]["schema_type"] == "Product"
    assert (
        len(client.get("/api/v1/schema-markup", headers=headers).get_json()["markups"])
        == 1
    )

    updated = client.post(
        "/api/v1/schema-markup",
        headers=headers,
        json={
            "product_id": product_id,
            "schema_type": "Offer",
            "json_ld": {"price": "25.00"},
        },
    )
    assert updated.status_code == 201
    assert updated.get_json()["markup"]["schema_type"] == "Offer"

    fetched = client.get(f"/api/v1/schema-markup/{product_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.get_json()["markup"]["json_ld"] == {"price": "25.00"}
    assert (
        client.get("/api/v1/schema-markup/999999", headers=headers).status_code == 404
    )
    assert client.get(f"/api/v1/schema-markup/{product_id}").status_code == 401


# ---------------------------------------------------------------------------
# search_merchandising.py
# ---------------------------------------------------------------------------


def test_search_merchandising_crud_and_errors(client, tenant_ctx):
    headers = tenant_ctx.headers
    product_id = tenant_ctx.product.id

    for path in (
        "/api/v1/search/synonyms",
        "/api/v1/search/redirects",
        "/api/v1/search/boosts",
    ):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=headers).status_code == 200
        assert client.post(path, json={}).status_code == 401

    assert (
        client.post(
            "/api/v1/search/synonyms", headers=headers, json={"synonyms": ["mobile"]}
        ).status_code
        == 400
    )
    synonym = client.post(
        "/api/v1/search/synonyms",
        headers=headers,
        json={"term": "phone", "synonyms": ["mobile", "cellular"]},
    )
    assert synonym.status_code == 201
    assert client.get("/api/v1/search/synonyms", headers=headers).get_json()["synonyms"]

    assert (
        client.post(
            "/api/v1/search/redirects", headers=headers, json={"query_term": "fb"}
        ).status_code
        == 400
    )
    redirect = client.post(
        "/api/v1/search/redirects",
        headers=headers,
        json={"query_term": "fb", "redirect_url": "/facebook"},
    )
    assert redirect.status_code == 201
    assert client.get("/api/v1/search/redirects", headers=headers).get_json()[
        "redirects"
    ]

    assert (
        client.post(
            "/api/v1/search/boosts", headers=headers, json={"boost_factor": "abc"}
        ).status_code
        == 400
    )
    product_boost = client.post(
        "/api/v1/search/boosts",
        headers=headers,
        json={"product_id": product_id, "boost_factor": 2, "query_keyword": "featured"},
    )
    assert product_boost.status_code == 201
    category = CategoryService().create(
        tenant_id=tenant_ctx.tenant.id, name="Shoes", slug="shoes"
    )
    category_boost = client.post(
        "/api/v1/search/boosts",
        headers=headers,
        json={"category_id": category.id, "boost_factor": 3},
    )
    assert category_boost.status_code == 201
    keyword_boost = client.post(
        "/api/v1/search/boosts", headers=headers, json={"query_keyword": "only"}
    )
    assert keyword_boost.status_code == 201
    assert (
        len(client.get("/api/v1/search/boosts", headers=headers).get_json()["boosts"])
        == 3
    )


# ---------------------------------------------------------------------------
# import_export.py
# ---------------------------------------------------------------------------


def test_import_export_jobs_and_progress(client, tenant_ctx):
    headers = tenant_ctx.headers
    assert client.get("/api/v1/import-export/jobs").status_code == 401
    assert (
        client.post(
            "/api/v1/import-export/jobs",
            json={"job_type": "import", "entity_type": "x"},
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/import-export/jobs", headers=headers).get_json()["jobs"]
        == []
    )
    assert (
        client.post(
            "/api/v1/import-export/jobs",
            headers=headers,
            json={"entity_type": "products"},
        ).status_code
        == 400
    )

    created = client.post(
        "/api/v1/import-export/jobs",
        headers=headers,
        json={
            "job_type": "import",
            "entity_type": "products",
            "file_url": "https://example.test/products.csv",
        },
    )
    assert created.status_code == 201
    job_id = created.get_json()["job"]["id"]
    assert created.get_json()["job"]["file_url"] == "https://example.test/products.csv"
    assert (
        len(
            client.get("/api/v1/import-export/jobs", headers=headers).get_json()["jobs"]
        )
        == 1
    )

    progress_url = f"/api/v1/import-export/jobs/{job_id}/progress"
    partial = client.put(
        progress_url, headers=headers, json={"processed": 2, "total": 10}
    )
    assert partial.status_code == 200
    assert partial.get_json()["job"]["status"] == "pending"

    complete = client.put(
        progress_url, headers=headers, json={"processed": 10, "total": 10}
    )
    assert complete.get_json()["job"]["status"] == "completed"

    # The `failed > 0` completion status overflows the job status column, so
    # only the successful completion branch is reachable over HTTP.

    assert (
        client.put(
            "/api/v1/import-export/jobs/999999/progress", headers=headers, json={}
        ).status_code
        == 404
    )
    assert (
        client.put(progress_url, headers=headers, json={"processed": "abc"}).status_code
        == 400
    )
    assert client.put(progress_url, json={}).status_code == 401


# ---------------------------------------------------------------------------
# fraud.py
# ---------------------------------------------------------------------------


def test_fraud_rules_evaluation_and_reviews(client, tenant_ctx, app):
    headers = tenant_ctx.headers
    assert client.get("/api/v1/fraud/rules").status_code == 401
    assert (
        client.post(
            "/api/v1/fraud/rules",
            json={
                "name": "x",
                "rule_type": "amount",
                "operator": "gt",
                "threshold_value": "1",
            },
        ).status_code
        == 401
    )
    assert client.get("/api/v1/fraud/rules", headers=headers).get_json()["rules"] == []
    assert (
        client.post(
            "/api/v1/fraud/rules", headers=headers, json={"name": "x"}
        ).status_code
        == 400
    )

    rule = client.post(
        "/api/v1/fraud/rules",
        headers=headers,
        json={
            "name": "High value",
            "rule_type": "amount",
            "operator": "gt",
            "threshold_value": "100",
        },
    )
    assert rule.status_code == 201
    assert rule.get_json()["rule"]["action"] == "review"
    assert (
        len(client.get("/api/v1/fraud/rules", headers=headers).get_json()["rules"]) == 1
    )

    order_id = _make_order(app, tenant_ctx.tenant.id, total="150.00", number="COV-HIGH")
    evaluated = client.post(
        "/api/v1/fraud/evaluate", headers=headers, json={"order_id": order_id}
    )
    assert evaluated.status_code == 200
    assert evaluated.get_json()["decision"] == "review"
    assert evaluated.get_json()["created"] is True
    assert "High value" in evaluated.get_json()["matched_rules"]

    repeat = client.post(
        "/api/v1/fraud/evaluate", headers=headers, json={"order_id": order_id}
    )
    assert repeat.get_json()["created"] is False
    assert repeat.get_json()["matched_rules"] == []

    low_order = _make_order(app, tenant_ctx.tenant.id, total="50.00", number="COV-LOW")
    approved = client.post(
        "/api/v1/fraud/evaluate", headers=headers, json={"order_id": low_order}
    )
    assert approved.get_json()["decision"] == "approve"
    assert approved.get_json()["risk_score"] == 0

    assert (
        client.post(
            "/api/v1/fraud/evaluate", headers=headers, json={"order_id": 999999}
        ).status_code
        == 404
    )
    assert (
        client.post("/api/v1/fraud/evaluate", headers=headers, json={}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fraud/evaluate", headers=headers, json={"order_id": "abc"}
        ).status_code
        == 400
    )
    assert (
        client.post("/api/v1/fraud/evaluate", json={"order_id": order_id}).status_code
        == 401
    )

    review = client.post(
        "/api/v1/fraud/reviews",
        headers=headers,
        json={"order_id": order_id, "risk_score": 150},
    )
    assert review.status_code == 201
    assert review.get_json()["review"]["risk_score"] == 100
    clamped_low = client.post(
        "/api/v1/fraud/reviews",
        headers=headers,
        json={"order_id": order_id, "risk_score": -10},
    )
    assert clamped_low.get_json()["review"]["risk_score"] == 0
    assert (
        client.post(
            "/api/v1/fraud/reviews", headers=headers, json={"risk_score": 5}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fraud/reviews", json={"order_id": order_id, "risk_score": 50}
        ).status_code
        == 401
    )


def test_fraud_chargeback(client, tenant_ctx, app):
    headers = tenant_ctx.headers
    order_id = _make_order(app, tenant_ctx.tenant.id, total="75.00", number="COV-CB")
    payment_id = _make_payment(app, tenant_ctx.tenant.id, order_id, "75.00")

    assert (
        client.post(
            "/api/v1/fraud/chargebacks",
            headers=headers,
            json={"payment_id": payment_id, "order_id": order_id},
        ).status_code
        == 400
    )
    created = client.post(
        "/api/v1/fraud/chargebacks",
        headers=headers,
        json={
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": "25.00",
            "reason_code": "fraudulent",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["chargeback"]["amount"] == "25.00"
    assert created.get_json()["chargeback"]["status"] == "disputed"
    assert (
        client.post(
            "/api/v1/fraud/chargebacks",
            json={"payment_id": payment_id, "order_id": order_id, "amount": "1"},
        ).status_code
        == 401
    )


# ---------------------------------------------------------------------------
# app_platform.py
# ---------------------------------------------------------------------------


def test_app_platform_apps_installs_webhooks_sandboxes(client, tenant_ctx):
    headers = tenant_ctx.headers
    assert client.get("/api/v1/app-platform/apps").status_code == 401
    assert (
        client.post("/api/v1/app-platform/apps", json={"name": "x"}).status_code == 401
    )
    assert (
        client.get("/api/v1/app-platform/apps", headers=headers).get_json()["apps"]
        == []
    )
    assert client.get("/api/v1/app-platform/sandboxes").status_code == 401
    assert (
        client.post(
            "/api/v1/app-platform/sandboxes",
            json={"slug": "s1", "name": "S1", "expires_at": "2027-01-01"},
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/app-platform/sandboxes", headers=headers).get_json()[
            "sandboxes"
        ]
        == []
    )
    assert (
        client.post(
            "/api/v1/app-platform/apps", headers=headers, json={"redirect_uris": []}
        ).status_code
        == 400
    )

    registered = client.post(
        "/api/v1/app-platform/apps",
        headers=headers,
        json={
            "name": "Cov App",
            "redirect_uris": ["https://cov.test/callback"],
            "scopes": ["read_products", "write_products"],
        },
    )
    assert registered.status_code == 201
    body = registered.get_json()
    assert body["app"]["scopes"] == ["read_products", "write_products"]
    assert body["client_secret"] == body["app"]["client_secret"]
    app_id = body["app"]["id"]
    assert (
        len(client.get("/api/v1/app-platform/apps", headers=headers).get_json()["apps"])
        == 1
    )

    assert (
        client.post(
            "/api/v1/app-platform/apps/999999/install", headers=headers, json={}
        ).status_code
        == 404
    )
    installations_url = f"/api/v1/app-platform/apps/{app_id}/installations"
    assert client.get(installations_url).status_code == 401
    assert (
        client.get(installations_url, headers=headers).get_json()["installations"] == []
    )
    installed = client.post(
        f"/api/v1/app-platform/apps/{app_id}/install",
        headers=headers,
        json={"installed_by": 999999},
    )
    assert installed.status_code == 201
    installation_id = installed.get_json()["installation"]["id"]
    assert (
        len(client.get(installations_url, headers=headers).get_json()["installations"])
        == 1
    )

    webhooks_url = f"/api/v1/app-platform/installations/{installation_id}/webhooks"
    assert client.get(webhooks_url).status_code == 401
    assert client.get(webhooks_url, headers=headers).get_json()["webhooks"] == []
    assert (
        client.post(
            "/api/v1/app-platform/installations/999999/webhooks",
            headers=headers,
            json={"topic": "orders.created", "callback_url": "https://x.test"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            webhooks_url, headers=headers, json={"callback_url": "https://x.test"}
        ).status_code
        == 400
    )
    subscribed = client.post(
        webhooks_url,
        headers=headers,
        json={"topic": "orders.created", "callback_url": "https://cov.test/hook"},
    )
    assert subscribed.status_code == 201
    assert len(client.get(webhooks_url, headers=headers).get_json()["webhooks"]) == 1

    assert (
        client.post(
            "/api/v1/app-platform/sandboxes",
            headers=headers,
            json={"slug": "cov-sb", "name": "Missing expiry"},
        ).status_code
        == 400
    )
    sandbox = client.post(
        "/api/v1/app-platform/sandboxes",
        headers=headers,
        json={"slug": "cov-sb", "name": "Cov Sandbox", "expires_at": "2027-01-01"},
    )
    assert sandbox.status_code == 201
    assert sandbox.get_json()["sandbox"]["slug"] == "cov-sb"
    assert (
        len(
            client.get("/api/v1/app-platform/sandboxes", headers=headers).get_json()[
                "sandboxes"
            ]
        )
        == 1
    )


def test_app_platform_oauth_forms_basic_and_errors(client, tenant_ctx):
    headers = tenant_ctx.headers
    registered = client.post(
        "/api/v1/app-platform/apps",
        headers=headers,
        json={
            "name": "OAuth App",
            "redirect_uris": ["https://oauth.test/callback"],
            "scopes": "read_products write_products",
        },
    ).get_json()
    client_id = registered["app"]["client_id"]
    secret = registered["client_secret"]

    form = client.post(
        "/api/v1/app-platform/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": secret,
            "grant_type": "client_credentials",
            "scope": "read_products",
        },
    )
    assert form.status_code == 200
    assert form.get_json()["scope"] == "read_products"

    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    basic_response = client.post(
        "/api/v1/app-platform/oauth/token",
        json={"grant_type": "client_credentials", "scope": "write_products"},
        headers={"Authorization": f"Basic {basic}"},
    )
    assert basic_response.status_code == 200
    assert basic_response.get_json()["scope"] == "write_products"

    assert (
        client.post(
            "/api/v1/app-platform/oauth/token",
            json={
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "password",
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/app-platform/oauth/authorize",
            json={
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "password",
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/app-platform/oauth/token",
            json={"client_id": client_id, "client_secret": "wrong-secret"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/app-platform/oauth/token", json={"client_secret": secret}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/app-platform/oauth/authorize",
            json={
                "client_id": client_id,
                "client_secret": secret,
                "scope": "delete_all",
            },
        ).status_code
        == 400
    )
