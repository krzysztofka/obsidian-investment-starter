"""Unit tests for individual portfolio alert rules."""

import os
import tempfile
from unittest.mock import patch

from alerts.context import AlertContext
from alerts.rules.allocation_drift import AllocationDriftRule
from alerts.rules.delisting_risk import DelistingRiskRule, parse_fund_size_to_millions
from alerts.rules.insider_selling import InsiderSellingRule
from alerts.rules.macro_yield_curve import MacroYieldCurveRule
from alerts.rules.overvalued import OvervaluedRule
from alerts.rules.stop_loss import StopLossRule
from model.asset import Asset


def test_overvalued_rule():
    rule = OvervaluedRule()
    ctx = AlertContext(config={"alerts": {"overvalued": {"enabled": True, "max_pe_ratio": 35.0}}})

    # Cash should not be evaluated
    cash = Asset(ticker="CASH", name="Cash", platform="Bank", asset_type="cash", pe_ratio=50.0)
    assert rule.evaluate(cash, ctx) is False

    # Normal valuation
    normal_stock = Asset(ticker="NORM", name="Normal", platform="Degiro", asset_type="equity", pe_ratio=25.0)
    assert rule.evaluate(normal_stock, ctx) is False

    # Overvalued
    expensive_stock = Asset(ticker="EXP", name="Expensive", platform="Degiro", asset_type="equity", pe_ratio=45.0)
    assert rule.evaluate(expensive_stock, ctx) is True

    # Missing P/E
    no_pe = Asset(ticker="NO_PE", name="No PE", platform="Degiro", asset_type="equity", pe_ratio=None)
    assert rule.evaluate(no_pe, ctx) is None

    # Disabled rule
    disabled_ctx = AlertContext(config={"alerts": {"overvalued": {"enabled": False}}})
    assert rule.evaluate(expensive_stock, disabled_ctx) is False


def test_delisting_risk_rule():
    rule = DelistingRiskRule()
    ctx = AlertContext(config={"alerts": {"delisting_risk": {"enabled": True, "min_aum_million": 50.0}}})

    # Equity without fund size should not trigger ETF delisting risk
    equity = Asset(ticker="AAPL", name="Apple", platform="Degiro", asset_type="equity")
    assert rule.evaluate(equity, ctx) is False

    # Large ETF
    large_etf = Asset(ticker="BIG_ETF", name="Big ETF", platform="Degiro", asset_type="etf", fund_size="5,000m Euro")
    assert rule.evaluate(large_etf, ctx) is False

    # Tiny ETF below 50M threshold
    tiny_etf = Asset(ticker="TINY_ETF", name="Tiny ETF", platform="Degiro", asset_type="etf", fund_size="25m Euro")
    assert rule.evaluate(tiny_etf, ctx) is True

    # Helper function parsing tests
    assert parse_fund_size_to_millions("1.5b USD") == 1500.0
    assert parse_fund_size_to_millions("100m EUR") == 100.0
    assert parse_fund_size_to_millions("500k") == 0.5


def test_allocation_drift_rule():
    rule = AllocationDriftRule()
    ctx = AlertContext(
        assets=[
            Asset(ticker="A1", name="A1", platform="Degiro", asset_type="equity", value_pln=25000.0),
            Asset(ticker="A2", name="A2", platform="Degiro", asset_type="equity", value_pln=75000.0),
        ],
        config={"alerts": {"allocation_drift": {"enabled": True, "max_portfolio_weight_pct": 20.0}}},
    )

    # Total value = 100,000 PLN
    # A1 weight = 25% > 20% -> triggers alert
    a1 = Asset(ticker="A1", name="A1", platform="Degiro", asset_type="equity", value_pln=25000.0)
    assert rule.evaluate(a1, ctx) is True

    # A3 with 10% weight
    a3 = Asset(ticker="A3", name="A3", platform="Degiro", asset_type="equity", value_pln=10000.0)
    assert rule.evaluate(a3, ctx) is False

    # Foundation assets (cash, gold, real estate) are excluded
    cash = Asset(ticker="PLN", name="Cash", platform="Bank", asset_type="cash", value_pln=50000.0)
    assert rule.evaluate(cash, ctx) is False


def test_stop_loss_rule():
    rule = StopLossRule()
    ctx = AlertContext(config={"alerts": {"stop_loss": {"enabled": True}}})

    # Current price above stop loss -> False
    asset_safe = Asset(ticker="SAFE", name="Safe", platform="Degiro", current_price=105.0)
    asset_safe.extra_properties["stop_loss"] = 90.0
    assert rule.evaluate(asset_safe, ctx) is False

    # Current price at or below stop loss -> True
    asset_breached = Asset(ticker="BREACH", name="Breach", platform="Degiro", current_price=88.0)
    asset_breached.extra_properties["stop_loss"] = 90.0
    assert rule.evaluate(asset_breached, ctx) is True

    # No stop loss defined
    asset_no_sl = Asset(ticker="NONE", name="None", platform="Degiro", current_price=100.0)
    assert rule.evaluate(asset_no_sl, ctx) is False


def test_insider_selling_rule():
    rule = InsiderSellingRule()
    ctx = AlertContext(config={"alerts": {"insider_selling": {"enabled": True}}})

    # Non-equity should be False
    etf = Asset(ticker="ETF1", name="ETF1", platform="Degiro", asset_type="etf")
    assert rule.evaluate(etf, ctx) is False

    # Without FINNHUB_API_KEY environment variable -> returns None
    with patch.dict(os.environ, {}, clear=True):
        stock = Asset(ticker="STK", name="Stock", platform="Degiro", asset_type="equity")
        assert rule.evaluate(stock, ctx) is None

    # With mocked Finnhub service returning True
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "dummy_key"}):
        with patch("integrations.finnhub.service.check_insider_sell", return_value=True):
            stock = Asset(ticker="STK", name="Stock", platform="Degiro", asset_type="equity", yahoo_ticker="STK")
            assert rule.evaluate(stock, ctx) is True


def test_macro_yield_curve_rule():
    with tempfile.TemporaryDirectory() as tmp_dir:
        macro_path = os.path.join(tmp_dir, "Macro.md")

        # Inverted spread (< 0 bps)
        with open(macro_path, "w", encoding="utf-8") as f:
            f.write("---\nyield_spread_10y_2y_bps: -25.5\n---\n")

        rule = MacroYieldCurveRule(macro_file_path=macro_path)
        ctx = AlertContext(config={"alerts": {"macro_yield_curve": {"enabled": True, "inversion_threshold_bps": 0.0}}})

        # Equities and cyclical holdings should trigger
        equity = Asset(ticker="MSFT", name="Microsoft", platform="Exante", asset_type="equity", portfolio="Aggressive")
        assert rule.evaluate(equity, ctx) is True

        # Safe haven assets (bonds, cash, gold) should NOT trigger
        bond = Asset(ticker="EDO", name="EDO Bond", platform="PKOBP", asset_type="bond", portfolio="Safety net")
        assert rule.evaluate(bond, ctx) is False

        # Positive spread (> 0 bps)
        with open(macro_path, "w", encoding="utf-8") as f:
            f.write("---\nyield_spread_10y_2y_bps: 45.0\n---\n")
        rule_normal = MacroYieldCurveRule(macro_file_path=macro_path)
        assert rule_normal.evaluate(equity, ctx) is False
