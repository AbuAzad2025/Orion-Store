from __future__ import annotations

from decimal import Decimal

from core.exceptions import NotFoundError
from orion.extensions import db
from tax.tax import TaxJurisdiction, TaxNexusRule, TaxRate


class TaxService:
    def create_jurisdiction(
        self,
        *,
        tenant_id: int,
        code: str,
        name: str,
        country_code: str,
        region: str | None = None,
    ) -> TaxJurisdiction:
        j = TaxJurisdiction(
            tenant_id=tenant_id,
            code=code.strip().lower(),
            name=name,
            country_code=country_code.upper(),
            region=region,
        )
        db.session.add(j)
        db.session.commit()
        return j

    def list_jurisdictions(self, tenant_id: int) -> list[TaxJurisdiction]:
        return TaxJurisdiction.query.filter_by(tenant_id=tenant_id).all()

    def set_rate(
        self,
        *,
        tenant_id: int,
        jurisdiction_id: int,
        rate: str | Decimal,
        product_tax_code: str | None = None,
        priority: int = 0,
    ) -> TaxRate:
        j = TaxJurisdiction.query.filter_by(
            id=jurisdiction_id, tenant_id=tenant_id
        ).first()
        if not j:
            raise NotFoundError("Jurisdiction not found.")
        tr = TaxRate(
            jurisdiction_id=jurisdiction_id,
            tenant_id=tenant_id,
            rate=Decimal(str(rate)),
            product_tax_code=product_tax_code,
            priority=priority,
        )
        db.session.add(tr)
        db.session.commit()
        return tr

    def compute_tax(
        self, *, tenant_id: int, subtotal: Decimal, shipping_address: dict | None = None
    ) -> Decimal:
        jurisdictions = TaxJurisdiction.query.filter_by(
            tenant_id=tenant_id, is_active=True
        ).all()
        total_tax = Decimal("0")
        for j in jurisdictions:
            rate = (
                TaxRate.query.filter_by(jurisdiction_id=j.id)
                .order_by(TaxRate.priority.asc())
                .first()
            )
            if not rate:
                continue
            taxable = subtotal
            if rate.is_compound:
                taxable += total_tax
            total_tax += taxable * rate.rate
        return total_tax.quantize(Decimal("0.01"))
