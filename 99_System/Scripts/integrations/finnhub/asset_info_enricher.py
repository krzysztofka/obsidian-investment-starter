import os
import sys
import copy
from typing import Optional

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
scripts_dir = os.path.dirname(integrations_dir)
for p in (scripts_dir, integrations_dir):
    if p not in sys.path:
        sys.path.append(p)

from integrations.base import BaseAssetInfoEnricher
from model.asset import Asset
from integrations.finnhub.service import (
    fetch_analyst_rating,
    check_insider_sell,
    apply_insider_sell_tag,
)


class FinnhubAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for Finnhub API.

    Provides analyst recommendation consensus trends and SEC insider trading / sentiment alerts.
    """

    @property
    def name(self) -> str:
        return "Finnhub"

    def can_enrich(self, asset: Asset) -> bool:
        """Finnhub supports equities and ETFs (skips cash)."""
        return asset.asset_type != 'cash'

    def _resolve_symbol(self, asset: Asset) -> Optional[str]:
        """Resolve ticker symbol suitable for Finnhub."""
        if asset.yahoo_ticker:
            return asset.yahoo_ticker.split('.')[0]
        if asset.ticker:
            return asset.ticker.split('.')[0]
        return None

    def enrich(self, asset: Asset) -> Optional[Asset]:
        """Fetch analyst ratings and insider sell alerts from Finnhub and return a cloned enriched Asset."""
        symbol = self._resolve_symbol(asset)
        if not symbol:
            return None

        print(f"Fetching Finnhub analyst rating for {symbol}...")
        rating = fetch_analyst_rating(symbol)

        cloned = copy.deepcopy(asset)

        # Check insider sell alert for equities
        is_selling = False
        if cloned.asset_type == 'equity':
            is_selling = check_insider_sell(symbol)
        cloned.tags = apply_insider_sell_tag(cloned.tags, is_selling)

        if rating:
            cloned.analyst_rating = rating

        if not rating and cloned.tags == (asset.tags or []):
            return None

        return cloned

