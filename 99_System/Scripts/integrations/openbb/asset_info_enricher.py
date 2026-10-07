import copy
import os
import sys

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
scripts_dir = os.path.dirname(integrations_dir)
for p in (scripts_dir, integrations_dir):
    if p not in sys.path:
        sys.path.append(p)

from model.asset import Asset

from integrations.base import BaseAssetInfoEnricher
from integrations.openbb.service import (
    fetch_openbb_data,
)


class OpenBBAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for OpenBB / Morningstar integration.

    Enriches assets with Morningstar star ratings, risk metrics, analyst consensus, and fundamental data.
    """

    @property
    def name(self) -> str:
        return "OpenBB"

    def can_enrich(self, asset: Asset) -> bool:
        """OpenBB enricher supports equities and ETFs (skips cash)."""
        return asset.asset_type != "cash"

    def _resolve_symbol(self, asset: Asset) -> str | None:
        """Resolve ticker symbol suitable for OpenBB / Morningstar queries."""
        if asset.yahoo_ticker:
            return asset.yahoo_ticker
        if asset.ticker:
            return asset.ticker
        return None

    def enrich(self, asset: Asset) -> Asset | None:
        """Fetch Morningstar ratings and OpenBB data to return a cloned enriched Asset."""
        symbol = self._resolve_symbol(asset)
        if not symbol:
            return None

        print(f"Fetching OpenBB / Morningstar ratings for {symbol}...")
        data = fetch_openbb_data(symbol)
        if not data:
            return None

        cloned = copy.deepcopy(asset)
        modified = False

        if data.get("morningstar_rating") and not cloned.morningstar_rating:
            cloned.morningstar_rating = data["morningstar_rating"]
            modified = True

        if data.get("morningstar_risk") and not cloned.morningstar_risk:
            cloned.morningstar_risk = data["morningstar_risk"]
            modified = True

        if data.get("analyst_rating") and not cloned.analyst_rating:
            cloned.analyst_rating = data["analyst_rating"]
            modified = True

        if data.get("pe_ratio") and cloned.pe_ratio is None:
            cloned.pe_ratio = data["pe_ratio"]
            modified = True

        if data.get("dividend_yield") and not cloned.dividend_yield:
            cloned.dividend_yield = data["dividend_yield"]
            modified = True

        if data.get("sector") and not cloned.sector:
            cloned.sector = data["sector"]
            modified = True

        if data.get("industry") and not cloned.industry:
            cloned.industry = data["industry"]
            modified = True

        if data.get("volatility") and not cloned.volatility:
            cloned.volatility = data["volatility"]
            modified = True

        if data.get("sharpe_ratio") is not None and cloned.sharpe_ratio is None:
            cloned.sharpe_ratio = data["sharpe_ratio"]
            modified = True

        if data.get("max_drawdown") and not cloned.max_drawdown:
            cloned.max_drawdown = data["max_drawdown"]
            modified = True

        if data.get("upside_potential") and not cloned.upside_potential:
            cloned.upside_potential = data["upside_potential"]
            modified = True

        if not modified:
            return None

        return cloned
