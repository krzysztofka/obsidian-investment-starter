import os
import sys
from typing import Any

from .base import BaseAlertRule

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class OvervaluedRule(BaseAlertRule):
    """Flags assets trading at excessive valuation multiples (P/E ratio above threshold)."""

    DEFAULT_THRESHOLD = 40.0

    @property
    def name(self) -> str:
        return "Overvalued"

    @property
    def tag(self) -> str:
        return "#alert/overvalued"

    @property
    def description(self) -> str:
        return "Trailing P/E ratio exceeds configured upper valuation limit."

    def evaluate(self, asset: Asset, context: Any) -> bool | None:
        # Do not evaluate cash or fixed assets without P/E concept
        if str(asset.asset_type).lower() in ("cash", "real estate", "gold"):
            return False

        cfg = context.get_alert_config("overvalued", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        threshold = self.DEFAULT_THRESHOLD
        if isinstance(cfg, dict):
            threshold = float(cfg.get("max_pe_ratio", self.DEFAULT_THRESHOLD))
        elif isinstance(cfg, (int, float)):
            threshold = float(cfg)

        if asset.pe_ratio is None:
            return None

        try:
            val = float(str(asset.pe_ratio).replace(",", ".").strip())
            return val > threshold
        except (ValueError, TypeError):
            return None
