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
from integrations.vanguard.service import fetch_vanguard_data


class VanguardAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for Vanguard ETFs.

    Assigns official Vanguard product website URLs (issuer_url) and fund metadata.
    """

    @property
    def name(self) -> str:
        return "Vanguard"

    def can_enrich(self, asset: Asset) -> bool:
        """Check if asset is an ETF and belongs to Vanguard."""
        if asset.asset_type != 'etf':
            return False
        if asset.issuer and asset.issuer.strip().lower() == 'vanguard':
            return True
        name_lower = (asset.name or '').lower()
        return 'vanguard' in name_lower or 'vngrd' in name_lower

    def enrich(self, asset: Asset) -> Optional[Asset]:
        """Fetch metadata and product URL from Vanguard and return enriched clone."""
        data = fetch_vanguard_data(
            ticker=asset.ticker,
            isin=asset.isin,
            name=asset.name,
            yahoo_ticker=asset.yahoo_ticker,
        )
        if not data:
            return None

        cloned = copy.deepcopy(asset)
        cloned.issuer = "Vanguard"
        if data.get('issuer_url'):
            cloned.issuer_url = data['issuer_url']

        return cloned
