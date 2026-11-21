from __future__ import annotations

from decimal import Decimal

from currency.currency_rate import CurrencyRate

from orion.extensions import db

DEFAULT_CURRENCY = "ILS"


def resolve_currency_for_tenant(tenant_id: int | None) -> str:
    """Resolve a tenant's default currency (``ILS`` when absent/invalid).

    Reads ``Tenant.default_currency`` so a store can transact in its own
    currency instead of the historical hard-coded ILS. Failures are swallowed
    on purpose: payment creation must never break because of a bad currency
    value, and the default preserves all existing ILS behaviour.
    """
    if tenant_id is None:
        return DEFAULT_CURRENCY
    try:
        from tenant.tenant import Tenant

        tenant = Tenant.query.get(tenant_id)
    except Exception:  # pragma: no cover - defensive: no app context / DB issue
        return DEFAULT_CURRENCY
    value = getattr(tenant, "default_currency", None) if tenant is not None else None
    if not value or not isinstance(value, str):
        return DEFAULT_CURRENCY
    code = value.strip().upper()
    if len(code) != 3 or not code.isalpha():
        return DEFAULT_CURRENCY
    return code


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
