# Azadexa (Orion Engine)

Multi-tenant e-commerce SaaS — **wave 0** foundation.

**Repository:** [github.com/AbuAzad2025/Orion-Store](https://github.com/AbuAzad2025/Orion-Store)

## Quick start

```powershell
.\scripts\dev.ps1 docker-up    # PostgreSQL + Redis
.\scripts\dev.ps1 test         # 12 pytest
.\scripts\dev.ps1 run          # Flask dev server
```

Health check: `GET http://127.0.0.1:5000/health`

## Wave 0–1 deliverables

- Flask app factory + `/health`
- **Wave 1:** tenants, users, RBAC models, middleware, auth/tenant APIs
- `core/constants.py`, `core/crypto.py`, `core/events.py`
- `tests/security/test_tenant_isolation.py` — **12 tests passing**

See `ORION-Project-Plan-Report.md` §0.12 for build order.  
**تتبع التنفيذ:** §0.15 في الخطة (علامات ✅ 🟡 📋 ⬜ 🔒§0).
