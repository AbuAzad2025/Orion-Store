"""Live FX rates are fetched from the provider and persisted for reuse."""

from __future__ import annotations

from decimal import Decimal

from currency.currency_rate import CurrencyRate
from currency_svc.currency_service import CurrencyService


def test_live_rate_is_fetched_and_persisted(app, monkeypatch):
    monkeypatch.setitem(app.config, "CURRENCY_LIVE_RATES", True)
    monkeypatch.setattr(
        "currency_svc.exchange_rate_provider.fetch_live_rate",
        lambda base, quote, url_template=None: Decimal("0.25"),
    )

    svc = CurrencyService()
    assert svc.convert(
        amount=Decimal("100"), from_currency="ILS", to_currency="USD"
    ) == Decimal("25.00")

    row = CurrencyRate.query.filter_by(from_currency="ILS", to_currency="USD").first()
    assert row is not None
    assert row.source == "live:exchangerate-api"
    assert float(row.rate) == 0.25

    info = svc.rate_info("ILS", "USD")
    assert info["live"] is True
    assert info["rate"] == "0.25"


def test_customer_fx_markup_is_applied(app, monkeypatch):
    monkeypatch.setitem(app.config, "CURRENCY_LIVE_RATES", True)
    monkeypatch.setitem(app.config, "CURRENCY_FX_MARKUP_PERCENT", 3)
    monkeypatch.setattr(
        "currency_svc.exchange_rate_provider.fetch_live_rate",
        lambda base, quote, url_template=None: Decimal("0.25"),
    )

    svc = CurrencyService()
    assert svc.convert(
        amount=Decimal("100"),
        from_currency="ILS",
        to_currency="USD",
        markup_percent=3,
    ) == Decimal("25.75")
    info = svc.rate_info("ILS", "USD")
    assert info["markup_percent"] == "3"
    assert info["customer_rate"].startswith("0.2575")


def test_testing_config_never_calls_network(app, monkeypatch):
    assert app.config["CURRENCY_LIVE_RATES"] is False

    def explode(*args, **kwargs):
        raise AssertionError("network must not be called in testing")

    monkeypatch.setattr("currency_svc.exchange_rate_provider.fetch_live_rate", explode)
    svc = CurrencyService()
    assert svc.convert(
        amount=Decimal("100"), from_currency="AAA", to_currency="BBB"
    ) == Decimal("100")
