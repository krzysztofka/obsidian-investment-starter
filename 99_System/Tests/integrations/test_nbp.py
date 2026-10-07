"""Unit tests for NBP macroeconomic data supplier."""

import unittest
from unittest.mock import MagicMock, patch

from integrations.nbp import NBPMacroSupplier


class TestNBPMacroSupplier(unittest.TestCase):
    """Test suite for NBPMacroSupplier exchange rates, gold fixing, and central bank rates."""

    @patch("integrations.nbp.macro_supplier.NBPMacroSupplier._get")
    def test_fetch_exchange_rates_mocked(self, mock_get):
        """Verify parsing NBP Table A currency exchange rates."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "table": "A",
                "no": "195/A/NBP/2026",
                "effectiveDate": "2026-10-05",
                "rates": [
                    {"currency": "dolar amerykański", "code": "USD", "mid": 3.9215},
                    {"currency": "euro", "code": "EUR", "mid": 4.2850},
                    {"currency": "funt szterling", "code": "GBP", "mid": 5.1230},
                    {"currency": "frank szwajcarski", "code": "CHF", "mid": 4.5610},
                ],
            }
        ]
        mock_get.return_value = mock_resp

        # Filtered currencies
        rates = NBPMacroSupplier.fetch_exchange_rates(target_currencies=["USD", "EUR"])
        self.assertEqual(len(rates), 2)
        self.assertEqual(rates["USD"], 3.9215)
        self.assertEqual(rates["EUR"], 4.2850)

        # All currencies
        all_rates = NBPMacroSupplier.fetch_exchange_rates(target_currencies=None)
        self.assertEqual(len(all_rates), 4)
        self.assertIn("GBP", all_rates)

    @patch("integrations.nbp.macro_supplier.NBPMacroSupplier._get")
    def test_fetch_gold_price_mocked(self, mock_get):
        """Verify parsing NBP gold fixing price and troy ounce calculation."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"data": "2026-10-05", "cena": 340.50}]
        mock_get.return_value = mock_resp

        gold = NBPMacroSupplier.fetch_gold_fixing()
        self.assertIsNotNone(gold)
        self.assertEqual(gold["price_1g_pln"], 340.50)
        expected_oz = 340.50 * NBPMacroSupplier.TROY_OUNCE_TO_GRAMS
        self.assertAlmostEqual(gold["price_oz_pln"], expected_oz, places=4)
        self.assertEqual(gold["date"], "2026-10-05")

    @patch("integrations.nbp.macro_supplier.NBPMacroSupplier._get")
    def test_fetch_base_rates_mocked(self, mock_get):
        """Verify parsing Polish central bank base interest rates from XML feed."""
        xml_content = b"""<?xml version="1.0" encoding="utf-8"?>
        <stopy_procentowe data_publikacji="2026-09-04">
            <tabela nr="09/2026">
                <pozycja id="ref" obowiazuje_od="2026-09-05" oprocentowanie="5,75" trend="spadek"/>
                <pozycja id="lom" obowiazuje_od="2026-09-05" oprocentowanie="6,25"/>
                <pozycja id="dep" obowiazuje_od="2026-09-05" oprocentowanie="5,25"/>
            </tabela>
        </stopy_procentowe>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = xml_content
        mock_get.return_value = mock_resp

        rates = NBPMacroSupplier.fetch_base_rates()
        self.assertEqual(rates["ref_rate"], 5.75)
        self.assertEqual(rates["lombard_rate"], 6.25)
        self.assertEqual(rates["deposit_rate"], 5.25)
        self.assertEqual(rates["trend"], "Easing / Cut")
        self.assertEqual(rates["last_decision_date"], "2026-09-04")
