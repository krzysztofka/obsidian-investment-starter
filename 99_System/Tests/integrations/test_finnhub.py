"""Unit tests for Finnhub API enricher and insider sentiment analytics."""

import unittest
from unittest.mock import MagicMock, patch

from integrations.finnhub import (
    ALERT_INSIDER_SELL_TAG,
    FinnhubAssetInfoEnricher,
    apply_insider_sell_tag,
    check_insider_sell,
)
from integrations.finnhub.service import (
    fetch_analyst_rating,
    fetch_insider_transactions,
)
from model.asset import Asset


class TestFinnhubEnricher(unittest.TestCase):
    """Test suite for FinnhubAssetInfoEnricher and insider trading monitoring."""

    def setUp(self):
        self.enricher = FinnhubAssetInfoEnricher()

    def test_can_enrich(self):
        """Verify asset types eligible for Finnhub enrichment."""
        equity_asset = Asset(ticker="NVDA", name="NVIDIA Corp", asset_type="equity")
        etf_asset = Asset(ticker="V80A", name="Vanguard LifeStrategy 80", asset_type="etf")
        cash_asset = Asset(ticker="EUR_CASH", name="EUR Cash", asset_type="cash")

        self.assertTrue(self.enricher.can_enrich(equity_asset))
        self.assertTrue(self.enricher.can_enrich(etf_asset))
        self.assertFalse(self.enricher.can_enrich(cash_asset))

    def test_apply_insider_sell_tag(self):
        """Verify applying and removing the #alert/insider_sell tag."""
        tags = ["#portfolio/growth"]
        with_alert = apply_insider_sell_tag(tags, is_insider_sell=True)
        self.assertIn(ALERT_INSIDER_SELL_TAG, with_alert)

        without_alert = apply_insider_sell_tag(with_alert, is_insider_sell=False)
        self.assertNotIn(ALERT_INSIDER_SELL_TAG, without_alert)
        self.assertIn("#portfolio/growth", without_alert)

    def test_check_insider_sell(self):
        """Verify insider selling evaluation using mocked Finnhub client."""
        mock_client = MagicMock()
        # Mock net selling sentiment (negative change and MSPR)
        mock_client.stock_insider_sentiment.return_value = {"data": [{"change": -10000, "mspr": -15.5}]}

        self.assertTrue(check_insider_sell("NVDA", finnhub_client=mock_client))

        # Mock net positive sentiment
        mock_client.stock_insider_sentiment.return_value = {"data": [{"change": 5000, "mspr": 12.0}]}
        self.assertFalse(check_insider_sell("NVDA", finnhub_client=mock_client))

        # Empty data
        mock_client.stock_insider_sentiment.return_value = {"data": []}
        mock_client.stock_insider_transactions.return_value = {"data": []}
        self.assertFalse(check_insider_sell("NVDA", finnhub_client=mock_client))

    def test_fetch_analyst_rating_mocked(self):
        """Verify parsing Finnhub analyst recommendation trends."""
        mock_client = MagicMock()
        mock_client.recommendation_trends.return_value = [
            {
                "buy": 25,
                "hold": 8,
                "period": "2026-10-01",
                "sell": 1,
                "strongBuy": 15,
                "strongSell": 0,
                "symbol": "NVDA",
            }
        ]

        rating = fetch_analyst_rating(symbol="NVDA", finnhub_client=mock_client)
        self.assertIsNotNone(rating)
        self.assertIn("Buy", rating)

    def test_fetch_insider_transactions_mocked(self):
        """Verify retrieving and parsing insider transaction data."""
        mock_client = MagicMock()
        mock_client.stock_insider_transactions.return_value = {
            "data": [
                {"name": "Huang Jen Hsun", "share": 1000000, "change": -20000, "transactionDate": "2026-09-20"},
                {"name": "Kress Colette", "share": 200000, "change": -5000, "transactionDate": "2026-09-18"},
            ],
            "symbol": "NVDA",
        }

        txs = fetch_insider_transactions(symbol="NVDA", finnhub_client=mock_client)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]["change"], -20000)

    @patch("integrations.finnhub.service.get_finnhub_client")
    def test_finnhub_no_api_key_graceful(self, mock_get_client):
        """Verify enricher gracefully handles missing API credentials."""
        mock_get_client.return_value = None

        rating = fetch_analyst_rating(symbol="NVDA", finnhub_client=None)
        self.assertIsNone(rating)
        is_selling = check_insider_sell(symbol="NVDA", finnhub_client=None)
        self.assertFalse(is_selling)
