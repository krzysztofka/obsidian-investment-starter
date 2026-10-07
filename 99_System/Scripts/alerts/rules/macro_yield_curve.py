import os
import sys
from typing import Any

import yaml

from .base import BaseAlertRule

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class MacroYieldCurveRule(BaseAlertRule):
    """Flags equities and cyclical assets when the US 10Y-2Y Treasury yield curve spread is inverted (< 0 bps)."""

    DEFAULT_INVERSION_THRESHOLD_BPS = 0.0

    def __init__(self, macro_file_path: str | None = None):
        self.macro_file_path = macro_file_path
        self._cached_spread_bps: float | None = None
        self._macro_checked: bool = False

    @property
    def name(self) -> str:
        return "Macro Inverted Yield Curve"

    @property
    def tag(self) -> str:
        return "#alert/macro_inverted_yield_curve"

    @property
    def description(self) -> str:
        return "US 10Y-2Y Treasury yield curve spread is inverted, signaling late-cycle recession risk for equities."

    def _get_yield_spread_bps(self) -> float | None:
        """Read current yield_spread_10y_2y_bps from 10_Finance/Macro.md frontmatter."""
        if self._macro_checked:
            return self._cached_spread_bps

        self._macro_checked = True
        target_path = self.macro_file_path
        if not target_path:
            system_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
            vault_root = os.path.abspath(os.path.join(system_dir, ".."))
            target_path = os.path.join(vault_root, "10_Finance", "Macro.md")

        if not os.path.exists(target_path):
            return None

        try:
            with open(target_path, encoding="utf-8") as f:
                content = f.read()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict) and "yield_spread_10y_2y_bps" in fm:
                        self._cached_spread_bps = float(fm["yield_spread_10y_2y_bps"])
        except Exception:
            pass

        return self._cached_spread_bps

    def evaluate(self, asset: Asset, context: Any) -> bool | None:
        # Cash, bonds, real estate, and physical gold are capital preservation / safe-haven assets, not recession-risk equities
        asset_type = str(asset.asset_type or "").strip().lower()
        if asset_type in ("cash", "bond", "real estate", "gold", "deposit"):
            return False

        cfg = context.get_alert_config("macro_yield_curve", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        threshold_bps = self.DEFAULT_INVERSION_THRESHOLD_BPS
        if isinstance(cfg, dict):
            threshold_bps = float(cfg.get("inversion_threshold_bps", self.DEFAULT_INVERSION_THRESHOLD_BPS))

        spread_bps = self._get_yield_spread_bps()
        if spread_bps is None:
            return None

        is_inverted = spread_bps < threshold_bps
        if is_inverted:
            # Trigger for equities and cyclical portfolio holdings
            portfolio = str(asset.portfolio or "").strip().lower()
            if asset_type == "equity" or portfolio in ("aggressive", "long term"):
                return True
            return False
        else:
            # Curve is normal / positive spread - clear the alert tag
            return False
