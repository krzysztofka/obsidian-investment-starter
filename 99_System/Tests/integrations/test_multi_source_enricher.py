"""Unit tests for MultiSourceAssetEnricher multi-provider merging engine."""

import unittest

from integrations.base import BaseAssetInfoEnricher
from integrations.multi_source_asset_enricher import MultiSourceAssetEnricher
from model.asset import Asset


class MockHighPriorityEnricher(BaseAssetInfoEnricher):
    """Mock enricher simulating a primary source like JustETF or Exante."""

    @property
    def name(self) -> str:
        return "MockHigh"

    def can_enrich(self, asset: Asset) -> bool:
        return True

    def enrich(self, asset: Asset) -> Asset | None:
        cloned = asset.model_copy(deep=True)
        cloned.dominant_sector = "Technology"
        cloned.country = "United States"
        cloned.tags = (cloned.tags or []) + ["#alert/overvalued"]
        cloned.analyst_rating = "Strong Buy"
        return cloned


class MockLowPriorityEnricher(BaseAssetInfoEnricher):
    """Mock enricher simulating a secondary source like Finnhub or Stooq."""

    @property
    def name(self) -> str:
        return "MockLow"

    def can_enrich(self, asset: Asset) -> bool:
        return True

    def enrich(self, asset: Asset) -> Asset | None:
        cloned = asset.model_copy(deep=True)
        # Should be ignored because MockHigh already set dominant_sector
        cloned.dominant_sector = "Financials"
        # Should be used because MockHigh did not provide pe_ratio or industry
        cloned.pe_ratio = 55.0
        cloned.industry = "Software - Infrastructure"
        cloned.tags = (cloned.tags or []) + ["#portfolio/growth"]
        cloned.analyst_rating = "Buy"
        return cloned


class TestMultiSourceAssetEnricher(unittest.TestCase):
    """Test suite for MultiSourceAssetEnricher priority resolution and field merging."""

    def test_priority_merging_and_field_fallback(self):
        """Verify higher-priority enricher takes precedence while fallback populates missing fields."""
        enricher_a = MockHighPriorityEnricher()
        enricher_b = MockLowPriorityEnricher()

        composite_enricher = MultiSourceAssetEnricher(enrichers=[enricher_a, enricher_b])

        original_asset = Asset(
            ticker="MSFT",
            name="Microsoft Corp",
            currency="USD",
            quantity=10,
            current_price=420.0,
            asset_type="equity",
            tags=["#core"],
        )

        enriched = composite_enricher.enrich(original_asset)

        self.assertIsNotNone(enriched)
        # MockHigh wins dominant_sector and country
        self.assertEqual(enriched.dominant_sector, "Technology")
        self.assertEqual(enriched.country, "United States")
        # MockLow populates fields not provided by MockHigh
        self.assertEqual(enriched.pe_ratio, 55.0)
        self.assertEqual(enriched.industry, "Software - Infrastructure")

        # Tags are aggregated across providers
        self.assertIn("#core", enriched.tags)
        self.assertIn("#alert/overvalued", enriched.tags)
        self.assertIn("#portfolio/growth", enriched.tags)

        # Analyst ratings from both sources are aggregated with source labels
        self.assertIsInstance(enriched.analyst_rating, list)
        self.assertIn("MockHigh: Strong Buy", enriched.analyst_rating)
        self.assertIn("MockLow: Buy", enriched.analyst_rating)

        # Immutability: original asset must remain unchanged
        self.assertIsNone(original_asset.dominant_sector)
        self.assertIsNone(original_asset.pe_ratio)
        self.assertEqual(original_asset.tags, ["#core"])

    def test_cash_asset_skips_market_enrichment(self):
        """Verify cash assets bypass equity/ETF enrichers and have value_pln calculated."""
        composite_enricher = MultiSourceAssetEnricher(enrichers=[MockHighPriorityEnricher()])

        cash_asset = Asset(
            ticker="EUR_CASH",
            name="EUR Cash",
            asset_type="cash",
            quantity=1000.0,
            current_price=1.0,
            currency="PLN",
            tags=["#alert/overvalued"],  # Alert tags should be stripped for cash
        )

        enriched = composite_enricher.enrich(cash_asset)
        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.dominant_sector, "Cash")
        self.assertIsNone(enriched.pe_ratio)
        self.assertNotIn("#alert/overvalued", enriched.tags)
