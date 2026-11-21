import os

import pytest

from orion.app import create_app
from tests.conftest import OrionTestClient


@pytest.fixture
def app():
    os.environ["FLASK_ENV"] = "testing"
    os.environ["DATABASE_URL"] = "postgresql://azadexa:123@localhost:5432/azadexa_test"
    os.environ["ENCRYPTION_KEY"] = "dev-only-change-me"
    return create_app("testing")


def test_dump(app):
    print("\nROUTES:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if "/impersonation/" in rule.rule or rule.rule == "/health":
            print(rule.rule, rule.endpoint, rule.methods)
    with app.test_client(use_cookies=True) as c:
        r = c.get("/health")
        print("HEALTH", r.status_code, r.get_json(silent=True) or r.data[:200])
