import pytest
import os
from orion.app import create_app


@pytest.fixture
def app():
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["FLASK_ENV"] = "testing"
    return create_app("testing")


def test_dump(app):
    print("\nROUTES:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if "impersonation" in rule.rule or rule.rule in ["/api/v1/auth/login"]:
            print(rule.rule, rule.endpoint, rule.methods)
    with app.test_client(use_cookies=True) as c:
        for path, payload in [
            (
                "/api/v1/platform/impersonation/start",
                {"email": "x@y.com", "password": "z"},
            ),
            ("/api/v1/auth/login", {"email": "x@y.com", "password": "z"}),
        ]:
            r = c.post(path, json=payload)
            print(path, r.status_code, r.get_json(silent=True) or r.data[:200])
