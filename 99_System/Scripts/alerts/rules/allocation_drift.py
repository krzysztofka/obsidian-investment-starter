import os
import sys
from typing import Any

from .base import BaseAlertRule

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class AllocationDriftRule(BaseAlertRule):
    """Flags single equity holdings that have outgrown prudent risk limits (> 15% of portfolio)."""

    DEFAULT_MAX_WEIGHT_PCT = 15.0

    @property
    def name(self) -> str:
        return "Allocation Drift"

    @property
    def tag(self) -> str:
        return "#alert/allocation_drift"

    @property
    def description(self) -> str:
        return "Single stock position exceeds maximum prudent portfolio concentration threshold (default: 15%)."

    def evaluate(self, asset: Asset, context: Any) -> bool | None:
        # Cash, physical gold, and real estate are foundation assets and excluded from single-stock concentration checks
        asset_type = str(asset.asset_type or "").lower().strip()
        if asset_type in ("cash", "real estate", "gold"):
            return False

        cfg = context.get_alert_config("allocation_drift", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        max_weight = self.DEFAULT_MAX_WEIGHT_PCT
        applies_to_etfs = False
        if isinstance(cfg, dict):
            max_weight = float(cfg.get("max_portfolio_weight_pct", self.DEFAULT_MAX_WEIGHT_PCT))
            applies_to_etfs = bool(cfg.get("applies_to_etfs", False))
        elif isinstance(cfg, (int, float)):
            max_weight = float(cfg)

        if asset_type == "etf" and not applies_to_etfs:
            return False

        total_val = getattr(context, "total_portfolio_value", 0.0)
        if total_val <= 0:
            return None

        val = float(asset.value_pln or 0.0)
        weight_pct = (val / total_val) * 100.0

        return weight_pct > max_weight
