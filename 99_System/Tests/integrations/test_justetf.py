"""Unit tests for JustETF API enricher and ETF metadata extraction."""

import unittest
from unittest.mock import MagicMock, patch

from integrations.justetf import (
    ALERT_DELISTING_RISK_TAG,
    JustETFAssetInfoEnricher,
    apply_delisting_risk_tag,
    check_delisting_risk,
)
from integrations.justetf.service import (
    fetch_justetf_data,
)
from model.asset import Asset


class TestJustETFEnricher(unittest.TestCase):
    """Test suite for JustETFAssetInfoEnricher and ETF look-through parsing."""

    def setUp(self):
        self.enricher = JustETFAssetInfoEnricher()

    def test_can_enrich(self):
        """Verify ETF assets are eligible while non-ETF/cash without ISIN are rejected."""
        valid_etf = Asset(ticker="VWCE", name="Vanguard All-World", isin="IE00BK5BQT80", asset_type="etf")
        etf_no_isin = Asset(ticker="V80A", name="Vanguard 80", isin=None, asset_type="etf")
        stock_asset = Asset(ticker="AAPL", name="Apple Inc.", isin=None, asset_type="equity")
        cash_asset = Asset(ticker="USD_CASH", name="Cash", asset_type="cash")

        self.assertTrue(self.enricher.can_enrich(valid_etf))
        self.assertTrue(self.enricher.can_enrich(etf_no_isin))
        self.assertFalse(self.enricher.can_enrich(stock_asset))
        self.assertFalse(self.enricher.can_enrich(cash_asset))

    def test_check_delisting_risk(self):
        """Verify fund size evaluation against minimum AUM threshold."""
        # Under 50M -> risk
        self.assertTrue(check_delisting_risk("EUR 25 m", threshold_m=50.0))
        self.assertTrue(check_delisting_risk("USD 15 m", threshold_m=50.0))
        self.assertTrue(check_delisting_risk(30.0, threshold_m=50.0))

        # Over 50M -> safe
        self.assertFalse(check_delisting_risk("EUR 150 m", threshold_m=50.0))
        self.assertFalse(check_delisting_risk("USD 2,500 m", threshold_m=50.0))
        self.assertFalse(check_delisting_risk(500.0, threshold_m=50.0))
        self.assertFalse(check_delisting_risk(None))

    def test_apply_delisting_risk_tag(self):
        """Verify adding and removing the #alert/delisting_risk tag."""
        tags = ["#portfolio/etf"]
        with_alert = apply_delisting_risk_tag(tags, fund_size="EUR 20 m", threshold_m=50.0)
        self.assertIn(ALERT_DELISTING_RISK_TAG, with_alert)

        without_alert = apply_delisting_risk_tag(with_alert, fund_size="EUR 800 m", threshold_m=50.0)
        self.assertNotIn(ALERT_DELISTING_RISK_TAG, without_alert)
        self.assertIn("#portfolio/etf", without_alert)

    @patch("integrations.justetf.service.resilient_get")
    def test_fetch_justetf_data_mocked(self, mock_get):
        """Verify parsing metadata fields from JustETF product page HTML."""
        html_content = """
        <html>
            <body>
                <table class="table">
                    <tr><td>Total expense ratio</td><td>0.22% p.a.</td></tr>
                    <tr><td>Fund size</td><td>EUR 5,420 m</td></tr>
                    <tr><td>Inception</td><td>2019-07-23</td></tr>
                    <tr><td>Distribution policy</td><td>Accumulating</td></tr>
                    <tr><td>Replication</td><td>Physical (Full replication)</td></tr>
                    <tr><td>Fund domicile</td><td>Ireland</td></tr>
                </table>
            </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_content
        mock_get.return_value = mock_resp

        data = fetch_justetf_data("IE00BK5BQT80")
        self.assertIsNotNone(data)
        self.assertEqual(data.get("ter"), "0.22% p.a.")
        self.assertEqual(data.get("fund_size"), "EUR 5,420 m")
        self.assertEqual(data.get("distribution_policy"), "Accumulating")
        self.assertEqual(data.get("replication"), "Physical (Full replication)")
        self.assertEqual(data.get("fund_domicile"), "Ireland")
