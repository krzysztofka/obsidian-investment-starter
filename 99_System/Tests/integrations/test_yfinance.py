"""Unit tests for Yahoo Finance API enricher and quantitative helpers."""

import unittest
from unittest.mock import patch

from integrations.yfinance import (
    ALERT_OVERVALUED_TAG,
    YFinanceAssetInfoEnricher,
    apply_overvalued_tag,
    check_overvalued,
)
from integrations.yfinance.service import calculate_rsi
from model.asset import Asset


class TestYFinanceEnricher(unittest.TestCase):
    """Test suite for YFinanceAssetInfoEnricher and associated analytics."""

    def setUp(self):
        self.enricher = YFinanceAssetInfoEnricher()

    def test_can_enrich(self):
        """Verify asset types eligible for YFinance enrichment."""
        equity_asset = Asset(ticker="AAPL", name="Apple Inc.", asset_type="equity")
        etf_asset = Asset(ticker="VWCE", name="Vanguard FTSE All-World", asset_type="etf")
        cash_asset = Asset(ticker="USD_CASH", name="USD Cash Balance", asset_type="cash")

        self.assertTrue(self.enricher.can_enrich(equity_asset))
        self.assertTrue(self.enricher.can_enrich(etf_asset))
        self.assertFalse(self.enricher.can_enrich(cash_asset))

    def test_check_overvalued(self):
        """Verify PE ratio evaluation against the overvalued threshold."""
        self.assertTrue(check_overvalued(45.5, threshold=40.0))
        self.assertFalse(check_overvalued(25.0, threshold=40.0))
        self.assertFalse(check_overvalued(40.0, threshold=40.0))
        self.assertFalse(check_overvalued(None))
        self.assertFalse(check_overvalued("invalid_pe"))

    def test_apply_overvalued_tag(self):
        """Verify adding and removing the #alert/overvalued tag based on PE."""
        # Add tag when overvalued
        tags = ["#portfolio/core"]
        result = apply_overvalued_tag(tags, pe_ratio=55.0, threshold=40.0)
        self.assertIn(ALERT_OVERVALUED_TAG, result)

        # Remove tag when no longer overvalued
        result_normal = apply_overvalued_tag(result, pe_ratio=22.0, threshold=40.0)
        self.assertNotIn(ALERT_OVERVALUED_TAG, result_normal)
        self.assertIn("#portfolio/core", result_normal)

    def test_calculate_rsi(self):
        """Verify Relative Strength Index computation."""
        # Insufficient data
        self.assertIsNone(calculate_rsi([100.0] * 5, period=14))

        # Monotonically increasing prices -> RSI should be 100.0
        increasing_prices = [10.0 + i for i in range(20)]
        self.assertEqual(calculate_rsi(increasing_prices, period=14), 100.0)

        # Fluctuating prices within normal boundaries
        prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
        ]
        rsi = calculate_rsi(prices, period=14)
        self.assertIsNotNone(rsi)
        self.assertGreater(rsi, 0.0)
        self.assertLess(rsi, 100.0)

    @patch("integrations.yfinance.asset_info_enricher.calculate_value_pln")
    @patch("integrations.yfinance.asset_info_enricher.fetch_yfinance_data")
    @patch("integrations.yfinance.asset_info_enricher.fetch_yfinance_analyst_rating")
    def test_enrich_asset_mocked(self, mock_rating, mock_yf_data, mock_calc_val):
        """Verify enrichment of an Asset with mocked Yahoo Finance metadata."""
        mock_yf_data.return_value = {
            "yahoo_ticker": "MSFT",
            "pe_ratio": 42.5,
            "dividend_yield": "0.75%",
            "market_cap": "3.1T",
            "country": "United States",
            "sector": "Technology",
            "industry": "Software—Infrastructure",
            "fifty_two_week_high": 450.0,
            "fifty_two_week_low": 350.0,
        }
        mock_calc_val.return_value = 16800.0
        mock_rating.return_value = "Buy"

        asset = Asset(
            ticker="MSFT",
            name="Microsoft Corp",
            quantity=10,
            current_price=420.0,
            currency="USD",
            asset_type="equity",
            tags=[],
        )

        enriched = self.enricher.enrich(asset)

        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.yahoo_ticker, "MSFT")
        self.assertEqual(enriched.pe_ratio, 42.5)
        self.assertEqual(enriched.market_cap, "3.1T")
        self.assertEqual(enriched.value_pln, 16800.0)
        self.assertEqual(enriched.analyst_rating, "Buy")
        # Overvalued PE > 40 triggers alert tag
        self.assertIn(ALERT_OVERVALUED_TAG, enriched.tags)
        # Verify original asset is not mutated
        self.assertEqual(asset.value_pln, 0.0)
        self.assertNotIn(ALERT_OVERVALUED_TAG, asset.tags)
