from typing import Optional, Any
from .base import BaseAlertRule
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


class InsiderSellingRule(BaseAlertRule):
    """Flags equities with net executive / insider selling activity reported via Finnhub."""

    DEFAULT_LOOKBACK_DAYS = 90

    @property
    def name(self) -> str:
        return "Insider Selling"

    @property
    def tag(self) -> str:
        return "#alert/insider_sell"

    @property
    def description(self) -> str:
        return "Net executive insider selling detected over recent lookback window (default: 90 days)."

    def evaluate(self, asset: Asset, context: Any) -> Optional[bool]:
        if str(asset.asset_type).lower() != "equity":
            return False

        cfg = context.get_alert_config("insider_selling", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        lookback_days = self.DEFAULT_LOOKBACK_DAYS
        if isinstance(cfg, dict):
            lookback_days = int(cfg.get("lookback_days", self.DEFAULT_LOOKBACK_DAYS))

        months = max(1, lookback_days // 30)

        # Try to use Finnhub service if available and API key configured
        api_key = os.environ.get("FINNHUB_API_KEY")
        if not api_key:
            # Finnhub not configured; preserve tag state
            return None

        try:
            from integrations.finnhub.service import check_insider_sell
            symbol = asset.yahoo_ticker or asset.ticker
            if not symbol:
                return None
            return check_insider_sell(symbol, months=months)
        except Exception:
            return None
