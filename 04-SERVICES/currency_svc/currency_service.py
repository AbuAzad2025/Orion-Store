from __future__ import annotations

from decimal import Decimal

from currency.currency_rate import CurrencyRate
from orion.extensions import db


class CurrencyService:
    def set_rate(
        self,
        *,
        from_currency: str,
        to_currency: str,
        rate: str | Decimal,
        source: str = "manual",
    ) -> CurrencyRate:
        cr = CurrencyRate(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            rate=Decimal(str(rate)),
            source=source,
        )
        db.session.add(cr)
        db.session.commit()
        return cr

    def convert(
        self, *, amount: Decimal, from_currency: str, to_currency: str
    ) -> Decimal:
        if from_currency.upper() == to_currency.upper():
            return amount
        rate = (
            CurrencyRate.query.filter_by(
                from_currency=from_currency.upper(), to_currency=to_currency.upper()
            )
            .order_by(CurrencyRate.created_at.desc())
            .first()
        )
        if not rate:
            rate = (
                CurrencyRate.query.filter_by(
                    from_currency=to_currency.upper(), to_currency=from_currency.upper()
                )
                .order_by(CurrencyRate.created_at.desc())
                .first()
            )
            if rate:
                return (amount / rate.rate).quantize(Decimal("0.01"))
            return amount
        return (amount * rate.rate).quantize(Decimal("0.01"))

    def latest_rate(self, from_currency: str, to_currency: str) -> Decimal | None:
        rate = (
            CurrencyRate.query.filter_by(
                from_currency=from_currency.upper(), to_currency=to_currency.upper()
            )
            .order_by(CurrencyRate.created_at.desc())
            .first()
        )
        return rate.rate if rate else None
