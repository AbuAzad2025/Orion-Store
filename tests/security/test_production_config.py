"""Production configuration guardrails (P0 hardening).

Each case runs in a fresh subprocess: ``create_app`` registers module-level
blueprints once, so multiple apps in one interpreter are not supported yet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = os.pathsep.join(
    str(ROOT / part)
    for part in (
        "02-CORE",
        "03-MODELS",
        "04-SERVICES",
        "05-API",
        "06-STOREFRONT",
        "07-ADMIN",
    )
)


def _run(code: str, **env: str) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = PYTHONPATH
    child_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_production_rejects_placeholder_secret() -> None:
    result = _run(
        "from orion.app import create_app; create_app('production')",
        SECRET_KEY="dev-only-change-me",
        JWT_SECRET_KEY="a-real-jwt-secret",
        ENCRYPTION_KEY="a-real-fernet-key",
    )
    assert result.returncode != 0
    assert "missing or placeholder secrets: SECRET_KEY" in result.stderr


def test_production_rejects_missing_encryption_key() -> None:
    result = _run(
        "from orion.app import create_app; create_app('production')",
        SECRET_KEY="a-real-secret-key",
        JWT_SECRET_KEY="a-real-jwt-secret",
        ENCRYPTION_KEY="",
    )
    assert result.returncode != 0
    assert "ENCRYPTION_KEY" in result.stderr


def test_production_uses_secure_cookies_and_hsts() -> None:
    code = """
from orion.app import create_app
app = create_app('production')
assert app.config['JWT_COOKIE_SECURE'] is True
assert app.config['SESSION_COOKIE_SECURE'] is True
assert app.config['PREFERRED_URL_SCHEME'] == 'https'
assert app.config['ENFORCE_HSTS'] is True
assert app.config['LOG_JSON'] is True
assert app.config['SENTRY_ENVIRONMENT'] == 'production'
with app.test_client() as client:
    response = client.get('/health')
    assert response.headers.get('Strict-Transport-Security') is not None
print('PRODUCTION_CONFIG_OK')
"""
    result = _run(
        code,
        SECRET_KEY="key_" + "x" * 60,
        JWT_SECRET_KEY="jwt_" + "y" * 60,
        ENCRYPTION_KEY=Fernet.generate_key().decode(),
        ORION_SKIP_RLS_CHECK="1",
    )
    assert result.returncode == 0, result.stderr
    assert "PRODUCTION_CONFIG_OK" in result.stdout
