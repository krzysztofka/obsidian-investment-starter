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
from integrations.stooq.service import resolve_stooq_ticker


class StooqAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for Stooq.pl / Stooq.com market charts and data.

    Resolves and populates the `stooq_ticker` symbol across equities (US, GPW, Europe),
    ETFs (US, UCITS), Polish & global bonds/yields (10ply.b), and precious metals (xauusd).
    """

    @property
    def name(self) -> str:
        return "Stooq"

    def can_enrich(self, asset: Asset) -> bool:
        """Stooq supports equities, ETFs, commodities, bonds, and currencies (cash excluded)."""
        if asset.asset_type == "cash":
            return False
        return True

    def enrich(self, asset: Asset) -> Optional[Asset]:
        """Resolve the Stooq ticker symbol and return an enriched clone of the Asset."""
        cloned = copy.deepcopy(asset)

        # If already specified manually, preserve it
        if getattr(cloned, 'stooq_ticker', None):
            return cloned

        stooq_sym = resolve_stooq_ticker(
            isin=cloned.isin,
            yahoo_ticker=cloned.yahoo_ticker,
            ticker=cloned.ticker,
            name=cloned.name,
            asset_type=cloned.asset_type,
            country=cloned.country,
            currency=cloned.currency,
        )

        if stooq_sym:
            cloned.stooq_ticker = stooq_sym

        return cloned
