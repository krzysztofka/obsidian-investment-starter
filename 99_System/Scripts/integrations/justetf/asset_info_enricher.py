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
from integrations.justetf.service import (
    apply_delisting_risk_tag,
    fetch_justetf_data,
    fetch_justetf_sectors,
)
from integrations.sector_classifier import determine_dominant_sector


class JustETFAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for JustETF.

    Specializes in European / UCITS ETF metadata including TER, AUM (fund size),
    replication method, domicile, distribution policy, and sector breakdown.
    """

    @property
    def name(self) -> str:
        return "JustETF"

    def _extract_isin(self, asset: Asset) -> str | None:
        """Extract ISIN from asset.isin or ticker."""
        if asset.isin and len(asset.isin) == 12 and asset.isin[:2].isalpha():
            return asset.isin
        if asset.ticker and len(asset.ticker) == 12 and asset.ticker[:2].isalpha():
            return asset.ticker
        return None

    def can_enrich(self, asset: Asset) -> bool:
        """JustETF supports ETFs with an ISIN code."""
        if asset.asset_type == "cash":
            return False
        return self._extract_isin(asset) is not None or asset.asset_type == "etf"

    def enrich(self, asset: Asset) -> Asset | None:
        """Fetch metadata from JustETF and return a new cloned and enriched Asset."""
        isin = self._extract_isin(asset)
        if not isin:
            return None

        print(f"Fetching JustETF info for {isin}...")
        data = fetch_justetf_data(isin)
        if not data:
            return None

        # Produce a cloned asset
        cloned = copy.deepcopy(asset)
        cloned.isin = isin
        cloned.justetf_url = data.get("justetf_url") or cloned.justetf_url
        if data.get("issuer_url"):
            cloned.issuer_url = data["issuer_url"]
        cloned.ter = data.get("ter") or cloned.ter
        cloned.fund_size = data.get("fund_size") or cloned.fund_size
        cloned.distribution_policy = data.get("distribution_policy") or cloned.distribution_policy
        cloned.replication = data.get("replication") or cloned.replication
        cloned.fund_domicile = data.get("fund_domicile") or cloned.fund_domicile

        # Merge tags (such as delisting risk)
        tags_list = list(cloned.tags) if cloned.tags else []
        if "tags" in data:
            for t in data["tags"]:
                if t not in tags_list:
                    tags_list.append(t)
        cloned.tags = apply_delisting_risk_tag(tags_list, cloned.fund_size)

        # Sector breakdown
        sectors = fetch_justetf_sectors(isin)
        if sectors:
            dom_sec = determine_dominant_sector(sectors)
            if dom_sec:
                cloned.dominant_sector = dom_sec
                cloned.industry = dom_sec

        return cloned
