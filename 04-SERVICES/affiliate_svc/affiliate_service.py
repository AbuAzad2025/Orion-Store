from __future__ import annotations

import uuid
from decimal import Decimal

from affiliate.affiliate import (
    Affiliate,
    AffiliateCommission,
    AffiliateLink,
    AffiliateProgram,
)

from core.exceptions import NotFoundError
from orion.extensions import db


class AffiliateService:
    def create_program(
        self,
        *,
        tenant_id: int,
        name: str,
        code: str,
        commission_type: str,
        commission_value: str | Decimal,
        cookie_days: int = 30,
    ) -> AffiliateProgram:
        p = AffiliateProgram(
            tenant_id=tenant_id,
            name=name,
            code=code.strip().lower(),
            commission_type=commission_type,
            commission_value=Decimal(str(commission_value)),
            cookie_days=cookie_days,
        )
        db.session.add(p)
        db.session.commit()
        return p

    def register_affiliate(
        self, *, tenant_id: int, program_id: int, email: str
    ) -> Affiliate:
        program = AffiliateProgram.query.filter_by(
            id=program_id, tenant_id=tenant_id
        ).first()
        if not program:
            raise NotFoundError("Program not found.")
        a = Affiliate(
            tenant_id=tenant_id,
            program_id=program_id,
            email=email.strip().lower(),
            referral_code=uuid.uuid4().hex[:8],
        )
        db.session.add(a)
        db.session.commit()
        return a

    def record_commission(
        self, *, tenant_id: int, affiliate_id: int, order_id: int, amount: str | Decimal
    ) -> AffiliateCommission:
        c = AffiliateCommission(
            tenant_id=tenant_id,
            affiliate_id=affiliate_id,
            order_id=order_id,
            amount=Decimal(str(amount)),
        )
        db.session.add(c)
        db.session.commit()
        return c

    def create_link(
        self, *, affiliate_id: int, url: str, product_id: int | None = None
    ) -> AffiliateLink:
        link = AffiliateLink(affiliate_id=affiliate_id, product_id=product_id, url=url)
        db.session.add(link)
        db.session.commit()
        return link
