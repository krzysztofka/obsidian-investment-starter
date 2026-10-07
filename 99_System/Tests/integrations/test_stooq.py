"""Unit tests for Stooq API enricher and market ticker resolution."""

import unittest

from integrations.stooq import (
    StooqAssetInfoEnricher,
    resolve_stooq_ticker,
)
from model.asset import Asset


class TestStooqEnricher(unittest.TestCase):
    """Test suite for Stooq ticker symbol resolution and asset enrichment."""

    def setUp(self):
        self.enricher = StooqAssetInfoEnricher()

    def test_resolve_stooq_ticker_known_isin(self):
        """Verify resolution of known ISINs to Stooq symbols."""
        # Polish equities
        self.assertEqual(resolve_stooq_ticker(isin="PLKGHM000017"), "kgh")
        self.assertEqual(resolve_stooq_ticker(isin="PLPKN0000018"), "pkn")

        # European UCITS ETFs
        self.assertEqual(resolve_stooq_ticker(isin="IE00BMVB5R75"), "v80a.de")
        self.assertEqual(resolve_stooq_ticker(isin="IE000YYE6WK5"), "dfen.de")

    def test_resolve_stooq_ticker_commodities_and_benchmarks(self):
        """Verify resolution of precious metals and macro benchmarks."""
        self.assertEqual(resolve_stooq_ticker(ticker="GOLD"), "xauusd")
        self.assertEqual(resolve_stooq_ticker(ticker="XAUUSD"), "xauusd")
        self.assertEqual(resolve_stooq_ticker(ticker="10PLY"), "10ply.b")

    def test_resolve_stooq_ticker_polish_retail_bonds(self):
        """Verify Polish retail treasury bonds map to 10-year benchmark 10ply.b."""
        self.assertEqual(resolve_stooq_ticker(ticker="EDO0936_20360901"), "10ply.b")
        self.assertEqual(resolve_stooq_ticker(ticker="ROD0838_20380826"), "10ply.b")
        self.assertEqual(resolve_stooq_ticker(ticker="OTS0127_20270101"), "10ply.b")

    def test_stooq_enricher_enrich_asset(self):
        """Verify StooqAssetInfoEnricher assigns stooq_ticker to Asset."""
        asset = Asset(
            ticker="V80A",
            name="Vanguard LifeStrategy 80",
            isin="IE00BMVB5R75",
            asset_type="etf",
        )
        enriched = self.enricher.enrich(asset)

        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.stooq_ticker, "v80a.de")
        # Ensure non-mutating deep copy
        self.assertIsNone(asset.stooq_ticker)
