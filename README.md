# Azadexa (Orion Engine)

Multi-tenant e-commerce SaaS — **Waves 0–12 complete** ✅ + **Admin shell hardened** ✅ (login/logout/profile/footer + 10 beta stores + tenant subdomain resolution).

**Current phase:** 13 — Frontend Deep Dive (luxury UI refactor for admin + storefront).  
**Repository:** [github.com/AbuAzad2025/Orion-Store](https://github.com/AbuAzad2025/Orion-Store)

## Database

**PostgreSQL** in every environment — development, CI tests, and production. There is no MySQL/SQLite production path.

| Environment | Docker compose | Port | Database |
|-------------|----------------|------|----------|
| Development | `docker-compose.dev.yml` | 5432 | `azadexa_dev` |
| Tests | `docker-compose.test.yml` | 5433 | `azadexa_test` |
| Staging | `docker-compose.staging.yml` | 5000 / 9090 / 3000 | `azadexa_staging` |
| Production | `docker-compose.prod.yml` | 5000 | `azadexa_prod` |
| CI (GitHub Actions) | Postgres 16 service | 5432 | `azadexa_test` |

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
| Platform admin | `/admin/login` | `admin@azadexa.com` / `Admin2026!` | Leave tenant slug empty |
| Tenant admin (e.g. beta-ramallah) | `/admin/login` | `ramallah@beta.azadexa.com` / `BetaStore2026!` | Tenant slug: `beta-ramallah` |

Logout and profile links are available in the sidebar on every admin page.

## Storefront access

Local testing options:

- **Query parameter preview:** `http://127.0.0.1:5000/?tenant_slug=beta-ramallah`
- **Subdomain preview:** run `powershell -ExecutionPolicy Bypass -File scripts/setup_local_hosts.ps1` as Administrator, then visit:
  - `http://beta-ramallah.local.azadexa:5000/`
  - `http://beta-nablus.local.azadexa:5000/`
  - etc.

Production: `https://{tenant.slug}.azadexa.com/` or custom domain.

## Wave 0–1 deliverables

- Flask app factory + `/health`
- **Wave 1:** tenants, users, RBAC models, middleware, auth/tenant APIs
- `core/constants.py`, `core/crypto.py`, `core/events.py`
- `tests/security/test_tenant_isolation.py` — tenant isolation on real PostgreSQL

See `ORION-Project-Plan-Report.md` §0.12 for build order and §0.16 for the next phase (Frontend Deep Dive).  
**تتبع التنفيذ:** §0.15–§0.16 في الخطة (علامات ✅ 🟡 📋 ⬜ 🔒§0).
