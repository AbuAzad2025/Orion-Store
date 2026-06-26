"""Tests for core.crypto."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from core.crypto import CryptoService, strip_gateway_secrets
from core.exceptions import CryptoError, ValidationError


def test_encrypt_decrypt_roundtrip():
    key = Fernet.generate_key().decode()
    crypto = CryptoService(key=key)
    secret = "sk_live_test_gateway_key"
    encrypted = crypto.encrypt(secret)
    assert encrypted != secret
    assert crypto.decrypt(encrypted) == secret


def test_encrypt_empty_raises():
    key = Fernet.generate_key().decode()
    crypto = CryptoService(key=key)
    with pytest.raises(ValidationError):
        crypto.encrypt("")


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(CryptoError):
        CryptoService(key=None)


def test_strip_gateway_secrets():
    payload = {
        "provider": "stripe",
        "is_enabled": True,
        "webhook_secret": "whsec_secret",
        "credentials_encrypted": "enc_blob",
    }
    cleaned = strip_gateway_secrets(payload)
    assert cleaned == {"provider": "stripe", "is_enabled": True}
