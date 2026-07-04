from __future__ import annotations

from compliance.compliance import (
    ConsentRecord,
    CookieConsentSetting,
    DataSubjectRequest,
    SsoProvider,
)
from core.exceptions import NotFoundError
from orion.extensions import db


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
        import uuid

        provider = SsoProvider(
            tenant_id=tenant_id,
            provider_type=provider_type,
            client_id=client_id,
            client_secret_hash=uuid.uuid4().hex,
            issuer_url=issuer_url,
        )
        db.session.add(provider)
        db.session.commit()
        return provider

    def list_sso(self, tenant_id: int) -> list[SsoProvider]:
        return SsoProvider.query.filter_by(tenant_id=tenant_id, is_active=True).all()
