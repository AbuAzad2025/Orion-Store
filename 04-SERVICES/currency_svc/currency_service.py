from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from currency.currency_rate import CurrencyRate
from sqlalchemy import func

from orion.extensions import db

DEFAULT_CURRENCY = "ILS"


def resolve_currency_for_tenant(tenant_id: int | None) -> str:
    """Resolve a tenant's default currency (ILS when absent/invalid)."""
    if tenant_id is None:
        return DEFAULT_CURRENCY
    try:
        from tenant.tenant import Tenant

        tenant = Tenant.query.get(tenant_id)
    except Exception:  # pragma: no cover - defensive outside app context
        return DEFAULT_CURRENCY
    value = getattr(tenant, "default_currency", None) if tenant is not None else None
    if not value or not isinstance(value, str):
        return DEFAULT_CURRENCY
    code = value.strip().upper()
    if len(code) != 3 or not code.isalpha():
        return DEFAULT_CURRENCY
    return code


def _setting(key: str, default):
    from flask import current_app, has_app_context

    if has_app_context():
        return current_app.config.get(key, default)
    return default


class CurrencyService:
    def set_rate(
        self,
        *,
        from_currency: str,
        to_currency: str,
        rate: str | Decimal,
        source: str = "manual",
    ) -> CurrencyRate:
        """Upsert today's rate for a pair (the table has a daily unique key)."""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        cr = CurrencyRate.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency,
            rate_date=func.current_date(),
        ).first()
        if cr is None:
            cr = CurrencyRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=Decimal(str(rate)),
                source=source,
            )
            db.session.add(cr)
        else:
            cr.rate = Decimal(str(rate))
            cr.source = source
        db.session.commit()
        return cr

    def _row(self, from_currency: str, to_currency: str) -> CurrencyRate | None:
        return (
            CurrencyRate.query.filter_by(
                from_currency=from_currency.upper(), to_currency=to_currency.upper()
            )
            .order_by(CurrencyRate.created_at.desc())
            .first()
        )

    def _stale(self, row: CurrencyRate | None) -> bool:
        if row is None or row.created_at is None:
            return True
        ttl = int(_setting("CURRENCY_RATE_TTL_SECONDS", 3600))
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created > timedelta(seconds=ttl)

    def refresh_live_rate(
        self, from_currency: str, to_currency: str
    ) -> CurrencyRate | None:
        """Fetch a real rate from the configured provider and persist it."""
        if not _setting("CURRENCY_LIVE_RATES", True):
            return None
        from currency_svc.exchange_rate_provider import fetch_live_rate

        rate = fetch_live_rate(
            from_currency,
            to_currency,
            _setting(
                "CURRENCY_RATE_PROVIDER_URL",
                "https://open.er-api.com/v6/latest/{base}",
            ),
        )
        if rate is None:
            return None
        return self.set_rate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            source="live:exchangerate-api",
        )

    def _rate_for_conversion(self, from_currency: str, to_currency: str):
        """Return (rate, inverted) using a fresh real rate when possible."""
        base, quote = from_currency.upper(), to_currency.upper()
        row = self._row(base, quote)

        inverse = False
        if row is None or (self._stale(row) and row.source != "live:exchangerate-api"):
            self.refresh_live_rate(base, quote)
            row = self._row(base, quote)
        if row is None:
            row = self._row(quote, base)
            inverse = row is not None
            if row is None or (
                self._stale(row) and row.source != "live:exchangerate-api"
            ):
                self.refresh_live_rate(quote, base)
                row = self._row(quote, base)
                inverse = row is not None
        if row is None:
            return None, False
        return row.rate, inverse

    def convert(
        self, *, amount: Decimal, from_currency: str, to_currency: str
    ) -> Decimal:
        if from_currency.upper() == to_currency.upper():
            return amount
        rate, inverse = self._rate_for_conversion(from_currency, to_currency)
        if rate is None:
            return amount
        result = amount / rate if inverse else amount * rate
        return result.quantize(Decimal("0.01"))

    def latest_rate(self, from_currency: str, to_currency: str) -> Decimal | None:
        rate, inverse = self._rate_for_conversion(from_currency, to_currency)
        return (Decimal(1) / rate) if (rate is not None and inverse) else rate

    def rate_info(self, from_currency: str, to_currency: str) -> dict | None:
        """Transparency data for the storefront footer."""
        base, quote = from_currency.upper(), to_currency.upper()
        if base == quote:
            return None
        # Ensure a real rate exists before reporting it (first render of a
        # newly selected currency would otherwise show no info line).
        self._rate_for_conversion(base, quote)
        row = self._row(base, quote)
        inverse = False
        if row is None:
            row = self._row(quote, base)
            inverse = row is not None
        if row is None:
            return None
        value = Decimal(1) / row.rate if inverse else row.rate
        rate_text = format(value, "f").rstrip("0").rstrip(".")
        return {
            "rate": rate_text or "0",
            "source": row.source,
            "date": str(row.rate_date),
            "live": row.source.startswith("live:"),
            "pair": f"{base}→{quote}" if not inverse else f"{quote}→{base}",
        }
