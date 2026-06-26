"""Fernet encryption for credentials_encrypted (MVP — §4.49)."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from core.exceptions import CryptoError, ValidationError


def _normalize_key(key: str | bytes) -> bytes:
    if isinstance(key, str):
        return key.encode("utf-8")
    return key


class CryptoService:
    """Encrypt/decrypt sensitive values at rest using Fernet."""

    def __init__(self, key: str | bytes | None = None) -> None:
        raw = key or os.environ.get("ENCRYPTION_KEY")
        if not raw:
            raise CryptoError("ENCRYPTION_KEY is not configured.")
        try:
            self._fernet = Fernet(_normalize_key(raw))
        except (ValueError, TypeError) as exc:
            raise CryptoError("Invalid ENCRYPTION_KEY.") from exc

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise ValidationError("Cannot encrypt empty value.")
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            raise ValidationError("Cannot decrypt empty value.")
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise CryptoError("Decryption failed — invalid token or key.") from exc


def strip_gateway_secrets(payload: dict) -> dict:
    """Remove denylisted keys from API response dicts."""
    from core.constants import GATEWAY_RESPONSE_DENYLIST

    return {k: v for k, v in payload.items() if k not in GATEWAY_RESPONSE_DENYLIST}
