import copy
import os
import sys

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset

from integrations.base import BaseAssetInfoEnricher
from integrations.exante.service import ExanteClient, get_exante_client


class ExanteAssetInfoEnricher(BaseAssetInfoEnricher):
    """Enricher that resolves Exante asset metadata using the Exante REST API."""

    def __init__(self, client: ExanteClient | None = None):
        self.client = client

    @property
    def name(self) -> str:
        return "Exante"

    def can_enrich(self, asset: Asset) -> bool:
        if not asset.ticker:
            return False
        # Applicable for Exante platform assets or Exante-formatted tickers (e.g. TICKER.EXCHANGE)
        platform_matches = (asset.platform or "").strip().lower() == "exante"
        has_exchange_suffix = "." in asset.ticker and not asset.ticker.startswith("EXANTE_CASH_")
        return platform_matches or has_exchange_suffix

    def enrich(self, asset: Asset) -> Asset | None:
        if not self.can_enrich(asset):
            return None

        client = self.client or get_exante_client()
        if not client:
            return None

        try:
            info = client.get_symbol_info(asset.ticker)
            if not info or not isinstance(info, dict):
                return None

            cloned = copy.deepcopy(asset)
            if not cloned.isin and info.get("isin"):
                cloned.isin = info["isin"]
            name_candidate = info.get("name") or info.get("description")
            if (not cloned.name or cloned.name == cloned.ticker) and name_candidate:
                cloned.name = str(name_candidate)
            if not cloned.currency and info.get("currency"):
                cloned.currency = str(info["currency"]).upper()

            return cloned
        except Exception:
            return None
