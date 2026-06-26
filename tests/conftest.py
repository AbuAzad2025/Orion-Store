"""Pytest configuration."""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

from orion.app import create_app
from orion.extensions import db


@pytest.fixture(scope="session")
def fernet_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def app(fernet_key: str):
    os.environ["ENCRYPTION_KEY"] = fernet_key
    os.environ["FLASK_ENV"] = "testing"
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
