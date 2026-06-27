"""Application exceptions."""

from __future__ import annotations


class OrionError(Exception):
    """Base error for domain and infrastructure failures."""

    status_code = 500
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class ValidationError(OrionError):
    status_code = 400
    message = "Validation failed."


class NotFoundError(OrionError):
    status_code = 404
    message = "Resource not found."


class AuthenticationError(OrionError):
    status_code = 401
    message = "Authentication required."


class AuthorizationError(OrionError):
    status_code = 403
    message = "Permission denied."


class CryptoError(OrionError):
    status_code = 500
    message = "Encryption operation failed."


class TemplateValidationError(ValidationError):
    message = "Document template validation failed."
