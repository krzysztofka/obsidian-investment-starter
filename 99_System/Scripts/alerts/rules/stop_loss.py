from typing import Optional, Any
from .base import BaseAlertRule
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class StopLossRule(BaseAlertRule):
    """Flags assets whose current price has fallen below the user-defined stop_loss level."""

    @property
    def name(self) -> str:
        return "Stop Loss"

    @property
    def tag(self) -> str:
        return "#alert/stop_loss"

    @property
    def description(self) -> str:
        return "Asset market price has hit or dropped below designated stop_loss price."

    def evaluate(self, asset: Asset, context: Any) -> Optional[bool]:
        cfg = context.get_alert_config("stop_loss", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        # Look for stop_loss in extra_properties or direct attributes
        stop_loss_val = getattr(asset, "stop_loss", None)
        if stop_loss_val is None and hasattr(asset, "extra_properties"):
            stop_loss_val = asset.extra_properties.get("stop_loss")

        if stop_loss_val is None:
            return False

        try:
            sl_price = float(str(stop_loss_val).replace(",", ".").strip())
            curr_price = float(asset.current_price or 0.0)
            if sl_price <= 0 or curr_price <= 0:
                return False
            return curr_price <= sl_price
        except (ValueError, TypeError):
            return False
