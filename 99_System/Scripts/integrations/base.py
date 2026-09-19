from abc import ABC, abstractmethod
from typing import Optional
import os
import sys

# Ensure scripts dir is in sys.path
scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class BaseAssetInfoEnricher(ABC):
    """Abstract base class for financial data integration enrichers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the integration enricher (e.g. 'JustETF', 'YFinance', 'Finnhub')."""
        pass

    def can_enrich(self, asset: Asset) -> bool:
        """Check if this enricher can process or provide data for the given asset."""
        return True

    @abstractmethod
    def enrich(self, asset: Asset) -> Optional[Asset]:
        """Enrich asset metadata and return a new cloned Asset object.

        Args:
            asset: Input Asset holding platform and existing information.

        Returns:
            A cloned Asset object populated with enricher-specific data, or None if unavailable.
        """
        pass
