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
from integrations.ishares.service import fetch_ishares_data


class ISharesAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for iShares (BlackRock) ETFs.

    Assigns official iShares product website URLs (issuer_url) and fund metadata.
    """

    @property
    def name(self) -> str:
        return "iShares"

    def can_enrich(self, asset: Asset) -> bool:
        """Check if asset is an ETF and belongs to iShares."""
        if asset.asset_type != "etf":
            return False
        if asset.issuer and asset.issuer.strip().lower() == "ishares":
            return True
        return "ishares" in (asset.name or "").lower() or "ishares" in (asset.ticker or "").lower()

    def enrich(self, asset: Asset) -> Asset | None:
        """Fetch metadata and product URL from iShares and return enriched clone."""
        data = fetch_ishares_data(
            ticker=asset.ticker,
            isin=asset.isin,
            name=asset.name,
            yahoo_ticker=asset.yahoo_ticker,
        )
        if not data:
            return None

        cloned = copy.deepcopy(asset)
        cloned.issuer = "iShares"
        if data.get("issuer_url"):
            cloned.issuer_url = data["issuer_url"]
        if not cloned.isin and data.get("isin"):
            cloned.isin = data["isin"]
        if not cloned.ter and data.get("ter"):
            cloned.ter = data["ter"]
        if not cloned.fund_size and data.get("fund_size"):
            cloned.fund_size = data["fund_size"]
        if not cloned.distribution_policy and data.get("distribution_policy"):
            cloned.distribution_policy = data["distribution_policy"]
        if not cloned.fund_domicile and data.get("domicile"):
            cloned.fund_domicile = data["domicile"]

        return cloned
