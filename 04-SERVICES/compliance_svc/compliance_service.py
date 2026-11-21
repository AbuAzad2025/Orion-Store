from __future__ import annotations

import hashlib
import hmac
import secrets

from compliance.compliance import (
    ConsentRecord,
    CookieConsentSetting,
    DataSubjectRequest,
    SsoProvider,
)
from flask import current_app

from core.exceptions import AuthenticationError, NotFoundError, ValidationError
from core.utils import utc_now
from order.order import Order
from orion.extensions import db
from user.user import User

# Salt namespace — changing this prefix invalidates previously stored hashes.
_SSO_HASH_NAMESPACE = "orion-sso-v1"


def _sso_hash_key(*, tenant_id: int) -> bytes:
    """Build the HMAC key (salt) for a tenant's SSO client secrets.

    The application SECRET_KEY keeps stored hashes useless if the database is
    dumped on its own; the tenant id prevents hash reuse across tenants.
    """
    secret_key = str(current_app.config.get("SECRET_KEY", ""))
    return f"{_SSO_HASH_NAMESPACE}:{secret_key}:{tenant_id}".encode("utf-8")


def hash_client_secret(client_secret: str, *, tenant_id: int) -> str:
    """Deterministic HMAC-SHA256 + salt hash of an SSO client secret."""
    return hmac.new(
        _sso_hash_key(tenant_id=tenant_id),
        client_secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class ComplianceService:
    def record_consent(
        self,
        *,
        tenant_id: int,
        customer_email: str,
        consent_type: str,
        granted: bool,
        ip_address: str | None = None,
    ) -> ConsentRecord:
        rec = ConsentRecord(
            tenant_id=tenant_id,
            customer_email=customer_email.strip().lower(),
            consent_type=consent_type,
            granted=granted,
            ip_address=ip_address,
        )
        db.session.add(rec)
        db.session.commit()
        return rec

    def create_data_request(
        self, *, tenant_id: int, customer_email: str, request_type: str
    ) -> DataSubjectRequest:
        req = DataSubjectRequest(
            tenant_id=tenant_id,
            customer_email=customer_email.strip().lower(),
            request_type=request_type,
        )
        db.session.add(req)
        db.session.commit()
        return req

    def upsert_cookie_settings(
        self,
        *,
        tenant_id: int,
        banner_message: str | None = None,
        is_active: bool = True,
    ) -> CookieConsentSetting:
        existing = CookieConsentSetting.query.filter_by(tenant_id=tenant_id).first()
        if existing:
            existing.banner_message = banner_message
            existing.is_active = is_active
        else:
            existing = CookieConsentSetting(
                tenant_id=tenant_id, banner_message=banner_message, is_active=is_active
            )
            db.session.add(existing)
        db.session.commit()
        return existing

    def create_sso(
        self,
        *,
        tenant_id: int,
        provider_type: str,
        client_id: str,
        client_secret: str,
        issuer_url: str | None = None,
    ) -> SsoProvider:
        provider = SsoProvider(
            tenant_id=tenant_id,
            provider_type=provider_type,
            client_id=client_id,
            client_secret_hash=hash_client_secret(client_secret, tenant_id=tenant_id),
            issuer_url=issuer_url,
        )
        db.session.add(provider)
        db.session.commit()
        return provider

    def list_sso(self, tenant_id: int) -> list[SsoProvider]:
        return SsoProvider.query.filter_by(tenant_id=tenant_id, is_active=True).all()

    def exchange_sso_code(
        self,
        *,
        tenant_id: int,
        provider_code: str | None,
        external_email: str | None,
        provider_type: str | None = None,
        client_id: str | None = None,
    ) -> User:
        """Validate an SSO code against an enabled tenant provider and return a user.

        There is no external provider call: ``provider_code`` is the secret that
        was registered for the provider and is compared (constant time) with the
        stored HMAC hash. An existing tenant user is reused; otherwise one is
        provisioned when the matched provider allows it.
        """
        code = str(provider_code or "").strip()
        email = str(external_email or "").strip().lower()
        if not code or not email:
            raise ValidationError("provider_code and external_email are required.")

        query = SsoProvider.query.filter_by(tenant_id=tenant_id, is_active=True)
        if provider_type:
            query = query.filter_by(provider_type=provider_type)
        if client_id:
            query = query.filter_by(client_id=client_id)

        expected = hash_client_secret(code, tenant_id=tenant_id)
        provider = next(
            (
                p
                for p in query.all()
                if hmac.compare_digest(p.client_secret_hash, expected)
            ),
            None,
        )
        if provider is None:
            # A disabled/unknown provider and a wrong code are indistinguishable
            # to the caller on purpose.
            raise AuthenticationError("No active SSO provider accepted this code.")

        user = User.query.filter_by(
            tenant_id=tenant_id, email=email, is_active=True, deleted_at=None
        ).first()
        if user is not None:
            return user

        if not provider.auto_provision:
            raise AuthenticationError("SSO provisioning is disabled for this provider.")

        from auth.auth_service import AuthService

        # SSO users cannot log in with a password: store an unusable, properly
        # hashed credential so the non-nullable column stays safe.
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=AuthService().hash_password(secrets.token_urlsafe(32)),
            is_customer=True,
            is_admin=False,
            is_superuser=False,
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def export_subject_data(self, *, tenant_id: int, request_id: int) -> dict:
        """Return a complete, tenant-scoped JSON payload for a data subject."""
        req = self._get_data_request(tenant_id=tenant_id, request_id=request_id)
        email = req.customer_email.strip().lower()
        orders = Order.query.filter_by(tenant_id=tenant_id, customer_email=email).all()
        user = User.query.filter_by(tenant_id=tenant_id, email=email).first()
        consents = ConsentRecord.query.filter_by(
            tenant_id=tenant_id, customer_email=email
        ).all()
        return {
            "request": req.to_dict(),
            "subject": {"email": email},
            "user": user.to_dict() if user else None,
            "orders": [order.to_dict() for order in orders],
            "consent_records": [record.to_dict() for record in consents],
        }

    def execute_subject_deletion(self, *, tenant_id: int, request_id: int) -> dict:
        """Anonymise a subject's PII without destroying financial records."""
        req = self._get_data_request(tenant_id=tenant_id, request_id=request_id)
        email = req.customer_email.strip().lower()
        anonymised_email = f"deleted-{req.id}@anonymised.invalid"
        now = utc_now()

        users = User.query.filter_by(tenant_id=tenant_id, email=email).all()
        for user in users:
            user.email = f"deleted-{user.public_id}@anonymised.invalid"
            user.first_name = None
            user.last_name = None
            user.password_hash = secrets.token_hex(32)
            user.is_active = False
            user.deleted_at = now

        orders = Order.query.filter_by(tenant_id=tenant_id, customer_email=email).all()
        for order in orders:
            order.customer_email = anonymised_email
            order.customer_first_name = None
            order.customer_last_name = None
            order.shipping_address = {}
            order.user_id = None
            order.is_guest = True

        consents = ConsentRecord.query.filter_by(
            tenant_id=tenant_id, customer_email=email
        ).all()
        for record in consents:
            record.customer_email = anonymised_email
            record.ip_address = None
            record.user_agent = None

        req.status = "completed"
        req.completed_at = now
        db.session.commit()
        return {
            "request": req.to_dict(),
            "anonymised_email": anonymised_email,
            "users_anonymised": len(users),
            "orders_anonymised": len(orders),
            "consent_records_anonymised": len(consents),
        }

    def get_data_request(
        self, *, tenant_id: int, request_id: int
    ) -> DataSubjectRequest:
        """Public tenant-scoped lookup used by self-service GDPR endpoints."""
        return self._get_data_request(tenant_id=tenant_id, request_id=request_id)

    @staticmethod
    def _get_data_request(*, tenant_id: int, request_id: int) -> DataSubjectRequest:
        req = DataSubjectRequest.query.filter_by(
            id=request_id, tenant_id=tenant_id
        ).first()
        if req is None:
            raise NotFoundError("Data subject request not found.")
        return req
