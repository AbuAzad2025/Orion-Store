from __future__ import annotations

from decimal import Decimal

from tax.tax import TaxJurisdiction, TaxNexusRule, TaxRate

from core.exceptions import NotFoundError
from orion.extensions import db


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
        self,
        tenant_id: int,
        subtotal: Decimal,
        shipping_address: dict | None = None,
        shipping_cost: Decimal | str | None = None,
    ) -> Decimal:
        """Resolve tax from the shipping address, not a global tenant rate.

        The most specific matching jurisdiction wins (country + region beats
        country only). Within that jurisdiction the first rate by priority —
        highest rate on a tie — is applied to the taxable amount. An address
        with no matching jurisdiction is tax-free, which keeps checkout safe
        for tenants that have not configured tax regions yet.
        """
        address = shipping_address or {}
        country = (
            str(address.get("country_code") or address.get("country") or "")
            .strip()
            .upper()
        )
        region = (
            str(
                address.get("region")
                or address.get("state")
                or address.get("province")
                or address.get("city")
                or ""
            )
            .strip()
            .lower()
        )
        if not country and not region:
            return Decimal("0.00")

        best_rate = None
        best_specificity = 0
        for j in TaxJurisdiction.query.filter_by(
            tenant_id=tenant_id, is_active=True
        ).all():
            j_country = (j.country_code or "").strip().upper()
            j_region = (j.region or "").strip().lower()
            country_match = bool(j_country and country and j_country == country)
            region_match = bool(j_region and region and j_region == region)

            if j_country and j_region:
                # A jurisdiction scoped to both fields must match both.
                if not (country_match and region_match):
                    continue
                specificity = 2
            elif j_country:
                if not country_match:
                    continue
                specificity = 1
            elif j_region:
                if not region_match:
                    continue
                specificity = 1
            else:
                continue

            rate = (
                TaxRate.query.filter_by(jurisdiction_id=j.id)
                .order_by(TaxRate.priority.asc(), TaxRate.rate.desc())
                .first()
            )
            if not rate:
                continue
            if specificity > best_specificity or (
                specificity == best_specificity
                and rate.rate > (best_rate.rate if best_rate else Decimal("0"))
            ):
                best_rate, best_specificity = rate, specificity

        if best_rate is None:
            return Decimal("0.00")

        taxable = Decimal(str(subtotal))
        if shipping_cost is not None:
            taxable += Decimal(str(shipping_cost))
        return (taxable * best_rate.rate).quantize(Decimal("0.01"))
