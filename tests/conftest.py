"""Pytest configuration — CI-first, PostgreSQL-only (production parity).

Database
--------
Production, development, and tests all target **PostgreSQL**. CI and local tests use
``DATABASE_URL`` (GitHub Actions service or ``docker-compose.test.yml`` on port 5433).
``USE_SQLITE_TESTS=1`` is an undocumented emergency fallback — not used in CI.

Teardown
--------
Every function-scoped test: ``drop_all`` → ``create_all`` → test → ``drop_all``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from core.events import clear_subscribers
from orion.app import create_app
from orion.config import testing_database_uri
from orion.extensions import db

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "unit: Pure logic — no route/HTTP (still uses real DB when ORM is touched).",
    )
    config.addinivalue_line(
        "markers",
        "integration: Full-stack checks — CHECK constraints, RLS path (PostgreSQL).",
    )
    config.addinivalue_line(
        "markers",
        "external: Third-party HTTP via VCR/live sandbox — optional, not in default CI.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "tests/integration/" in path:
            if not item.get_closest_marker("integration"):
                item.add_marker(pytest.mark.integration)


# ---------------------------------------------------------------------------
# Environment — CI sets DATABASE_URL to the Postgres service container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def fernet_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture(scope="session")
def database_url() -> str:
    """PostgreSQL URI — same dialect as production."""
    return testing_database_uri()


@pytest.fixture(scope="session", autouse=True)
def _require_postgresql(database_url: str) -> None:
    """Fail fast if test DB is not reachable — keeps dev/CI aligned with production."""
    if database_url.startswith("sqlite"):
        if os.environ.get("USE_SQLITE_TESTS") != "1":
            pytest.exit(
                "Tests require PostgreSQL (production database). "
                "Run: .\\scripts\\dev.ps1 docker-test-up  "
                "Emergency SQLite only: USE_SQLITE_TESTS=1",
                returncode=1,
            )
        return

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.exit(
            "Cannot connect to PostgreSQL for tests. "
            f"URL={database_url!r}. "
            "Run: .\\scripts\\dev.ps1 docker-test-up\n"
            f"Detail: {exc}",
            returncode=1,
        )
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def uses_postgresql(database_url: str) -> bool:
    return database_url.startswith("postgresql")


@pytest.fixture(scope="session")
def app(fernet_key: str, database_url: str) -> Generator[Flask, None, None]:
    os.environ["ENCRYPTION_KEY"] = fernet_key
    os.environ["FLASK_ENV"] = "testing"
    os.environ["DATABASE_URL"] = database_url
    application = create_app("testing")
    yield application


# ---------------------------------------------------------------------------
# Per-function schema lifecycle — explicit teardown after every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_event_bus() -> Generator[None, None, None]:
    clear_subscribers()
    yield
    clear_subscribers()


@pytest.fixture(autouse=True)
def database_tables(app: Flask) -> Generator[None, None, None]:
    """Fresh schema per test; explicit drop_all teardown prevents state pollution."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# Flask HTTP client — native request/session context (no manual app_context)
# ---------------------------------------------------------------------------


class OrionTestClient:
    """Thin wrapper around Flask's test_client for production-like request handling."""

    def __init__(self, flask_client: FlaskClient) -> None:
        self._client = flask_client

    def get(self, *args, **kwargs) -> TestResponse:
        return self._client.get(*args, **kwargs)

    def post(self, *args, **kwargs) -> TestResponse:
        return self._client.post(*args, **kwargs)

    def put(self, *args, **kwargs) -> TestResponse:
        return self._client.put(*args, **kwargs)

    def patch(self, *args, **kwargs) -> TestResponse:
        return self._client.patch(*args, **kwargs)

    def delete(self, *args, **kwargs) -> TestResponse:
        return self._client.delete(*args, **kwargs)

    @property
    def flask_client(self) -> FlaskClient:
        return self._client


@pytest.fixture
def client(app: Flask) -> Generator[OrionTestClient, None, None]:
    """Flask test client with cookie/session support — mirrors production request stack."""
    with app.test_client(use_cookies=True) as flask_client:
        yield OrionTestClient(flask_client)


@pytest.fixture
def db_session(app: Flask):
    """SQLAlchemy session for direct persistence assertions (never mock this)."""
    with app.app_context():
        yield db.session


# ---------------------------------------------------------------------------
# Shared actors
# ---------------------------------------------------------------------------


@pytest.fixture
def platform_admin(app: Flask):
    from types import SimpleNamespace

    from auth.auth_service import AuthService

    with app.app_context():
        user = AuthService().register_super_admin(
            email="owner@azadexa.com", password="password123"
        )
        return SimpleNamespace(
            public_id=str(user.public_id),
            email=user.email,
        )


@pytest.fixture
def platform_admin_headers(platform_admin):
    from support.http import auth_headers

    return auth_headers(platform_admin)
