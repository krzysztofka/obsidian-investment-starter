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
from integrations.vaneck.service import fetch_vaneck_data


class VanEckAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for VanEck ETFs.

    Assigns official VanEck product website URLs (issuer_url) and fund metadata.
    """

    @property
    def name(self) -> str:
        return "VanEck"

    def can_enrich(self, asset: Asset) -> bool:
        """Check if asset is an ETF and belongs to VanEck."""
        if asset.asset_type != "etf":
            return False
        if asset.issuer and asset.issuer.strip().lower() == "vaneck":
            return True
        name_lower = (asset.name or "").lower()
        return "vaneck" in name_lower

    def enrich(self, asset: Asset) -> Asset | None:
        """Fetch metadata and product URL from VanEck and return enriched clone."""
        data = fetch_vaneck_data(
            ticker=asset.ticker,
            isin=asset.isin,
            name=asset.name,
            yahoo_ticker=asset.yahoo_ticker,
        )
        if not data:
            return None

        cloned = copy.deepcopy(asset)
        cloned.issuer = "VanEck"
        if data.get("issuer_url"):
            cloned.issuer_url = data["issuer_url"]
        if not cloned.ter and data.get("ter"):
            cloned.ter = data["ter"]
        if not cloned.fund_size and data.get("fund_size"):
            cloned.fund_size = data["fund_size"]

        return cloned
