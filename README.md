# Azadexa (Orion Engine)

Multi-tenant e-commerce SaaS — **wave 0** foundation.

**Repository:** [github.com/AbuAzad2025/Orion-Store](https://github.com/AbuAzad2025/Orion-Store)

## Quick start

```bash
# 1. Infrastructure
docker compose -f 01-FOUNDATION/infrastructure/docker-compose.dev.yml up -d

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# 3. Environment
copy .env.example .env
# Set ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Run
set FLASK_APP=orion.wsgi:app
set PYTHONPATH=02-CORE;03-MODELS;05-API
flask run

# 5. Test
pytest -v
```

Health check: `GET http://127.0.0.1:5000/health`

## Wave 0 deliverables

- Flask app factory + `/health`
- `core/constants.py`, `core/crypto.py` (Fernet), `core/events.py`
- `base/base_model.py` shell
- API blueprint skeleton (`/api/v1/*`, `/webhooks`)
- Docker: PostgreSQL 16 + Redis 7
- CI: black, isort, flake8, pytest, file-length check

See `ORION-Project-Plan-Report.md` §0.12 for build order.  
**تتبع التنفيذ:** §0.15 في الخطة (علامات ✅ 🟡 📋 ⬜ 🔒§0).
