# Azadexa (Orion Engine)

Multi-tenant e-commerce SaaS — **wave 0–1** foundation.

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

## Wave 0–1 deliverables

- Flask app factory + `/health`
- **Wave 1:** tenants, users, RBAC models, middleware, auth/tenant APIs
- `core/constants.py`, `core/crypto.py`, `core/events.py`
- `tests/security/test_tenant_isolation.py` — tenant isolation on real PostgreSQL

See `ORION-Project-Plan-Report.md` §0.12 for build order.  
**تتبع التنفيذ:** §0.15 في الخطة (علامات ✅ 🟡 📋 ⬜ 🔒§0).
