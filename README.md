# Azadexa (Orion Engine)

Multi-tenant e-commerce SaaS — **Waves 0–15 complete** ✅ + **Full-stack consistency audits (3 rounds)** ✅.

**Current status:** production-ready technical core; remaining work is deployment/ops (secrets, TLS, merchant accounts, load test).
**Repository:** [github.com/AbuAzad2025/Orion-Store](https://github.com/AbuAzad2025/Orion-Store)

> **أرقام مُتحقَّق منها من الكود (2026-11-21):** 112 صنف `db.Model`، 113 جدولاً في
> الهجرات، 101 جدولاً محمياً بـ RLS، ~100 نقطة API، 575 اختباراً ناجحاً. الأرقام الأكبر الواردة
> في `ORION-Project-Plan-Report.md` هي أهداف تخطيطية وليست حالة الكود. انظر
> `PRODUCTION-READINESS-PLAN.md` و `ADR/0001-source-of-truth.md`.

## Database

**PostgreSQL** in every environment — development, CI tests, and production. There is no MySQL/SQLite production path.

| Environment | Docker compose | Port | Database |
|-------------|----------------|------|----------|
| Development | `docker-compose.dev.yml` | 5432 | `azadexa_dev` |
| Tests | `docker-compose.test.yml` | 5433 | `azadexa_test` |
| Staging | `docker-compose.staging.yml` | 5000 / 9090 / 3000 | `azadexa_staging` |
| Production | `docker-compose.prod.yml` | 5000 | `azadexa_prod` |
| CI (GitHub Actions) | Postgres 15 service | 5432 | `orion_test_db` |

## Quick start (Windows — native PostgreSQL)

**Prerequisites:** Python 3.11+, PostgreSQL 16+ (service running), Git.

```powershell
.\scripts\dev.ps1 setup-local   # PG user/DBs, .env, Redis, migrate, seed
.\scripts\dev.ps1 run           # API on http://127.0.0.1:5000
.\scripts\dev.ps1 test            # pytest + coverage ≥85%
.\scripts\dev.ps1 launch-verify   # /health + /ready
```

**With Docker** (optional — if Docker Desktop installed):

```powershell
.\scripts\dev.ps1 docker-up        # PostgreSQL + Redis (dev)
.\scripts\dev.ps1 docker-test-up   # PostgreSQL test DB on port 5433
```

**Staging / production:**

```powershell
.\scripts\dev.ps1 docker-staging-up   # full staging stack (API + Prometheus + Grafana)
.\scripts\dev.ps1 docker-prod-up      # production stack
.\scripts\dev.ps1 backup-db           # PostgreSQL dump
```

Health check: `GET http://127.0.0.1:5000/health`

## Admin access

| Role | URL | Credentials | Notes |
|------|-----|-------------|-------|
| Platform admin | `/admin/login` | **يُنشأ يدوياً** — لا توجد كلمة مرور ثابتة في الكود | شغّل `python scripts/bootstrap_cli.py` وأدخل الإيميل/كلمة المرور (المسار الوحيد لأول أدمن). `setup-local` لا ينشئ أدمن منصة. |
| Tenant admin (e.g. beta-ramallah) | `/admin/login` | بيانات الدخول تُطبعها `scripts/seed_beta.py` عند البذر (عشوائية، لا ثابتة) | Tenant slug: `beta-ramallah` |

Logout and profile links are available in the sidebar on every admin page.

## Storefront access

Local testing options:

- **Query parameter preview:** `http://127.0.0.1:5000/?tenant_slug=beta-ramallah`
- **Subdomain preview:** run `powershell -ExecutionPolicy Bypass -File scripts/setup_local_hosts.ps1` as Administrator, then visit:
  - `http://beta-ramallah.local.azadexa:5000/`
  - `http://beta-nablus.local.azadexa:5000/`
  - etc.

Production: `https://{tenant.slug}.azadexa.com/` or custom domain.

## Customer & storefront self-service

- `/account` lets a logged-in customer view orders, export/delete personal data (GDPR),
  subscribe to plans, view store credit, submit B2B quote requests and create gift registries.
- Storefront header includes locale (`?locale=ar|en`) and currency (`?currency=ILS|USD|...`)
  switchers; translated product slugs and locale-aware UI strings are supported.
- Checkout supports address-based tax, store credit, coupons and optional BOPIS pickup.
- Admin login supports SSO exchange for enabled tenant identity providers.

## Demo data (local testing)
```powershell
# fresh DB + migrations, then:
DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/seed_demo_data.py
DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/fetch_product_images.py
DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/seed_translations.py
```
Seeds 5 tenants (`outlet`, `gulf`, `euro`, `atlantic`, `sterling`) with 12 products,
6 categories, 2 warehouses, 4 customers, 8 paid orders, 1 partial refund,
invoices, commissions, store credit, vouchers, gift registries and real FX rates.
Free-stock product photos are downloaded into the configured `PRODUCT_IMAGES_DIR`
(outside the application source tree) and attached to every product. Set
`PRODUCT_IMAGES_DIR=/srv/apps/orionstore/shared/product-images` in production.
Admin logins: `admin@<slug>.test` / `password123`.
Re-running skips existing tenants.

Verify the full purchase/refund/ledger cycle (see `docs/ACCOUNTING_AUDIT.md`):
```powershell
DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/verify_accounting_flow.py outlet
```

Audit Arabic/English consistency across all pages (see `docs/TRANSLATION_AUDIT.md`):
```powershell
DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/audit_translation.py
```

## Wave 0–1 deliverables

- Flask app factory + `/health`
- **Wave 1:** tenants, users, RBAC models, middleware, auth/tenant APIs
- `core/constants.py`, `core/crypto.py`, `core/events.py`
- `tests/security/test_tenant_isolation.py` — tenant isolation on real PostgreSQL

See `ORION-Project-Plan-Report.md` §0.12 for build order and §0.16 for the next phase (Frontend Deep Dive).
**تتبع التنفيذ:** §0.15–§0.16 في الخطة (علامات ✅ 🟡 📋 ⬜ 🔒§0).
