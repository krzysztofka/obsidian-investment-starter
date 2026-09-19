import re
from typing import Optional, Any, Union
from .base import BaseAlertRule
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(os.path.dirname(current_dir))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


def parse_fund_size_to_millions(fund_size: Optional[Union[str, int, float]]) -> Optional[float]:
    """Parse raw fund size string into float millions (EUR/USD)."""
    if fund_size is None:
        return None
    if isinstance(fund_size, (int, float)):
        val = float(fund_size)
        return val / 1_000_000.0 if val > 100_000 else val

    fs_str = str(fund_size).strip()
    if not fs_str or fs_str.lower() in ("null", "none", "nan", "-"):
        return None

    # Billion match
    b_match = re.search(r'([\d\.,]+)\s*(?:b|billion|mld)\b', fs_str, re.IGNORECASE)
    if b_match:
        val_str = b_match.group(1).replace(',', '.')
        if val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
        try:
            return float(val_str) * 1000.0
        except ValueError:
            pass

    # Million match
    m_match = re.search(r'([\d\.,]+)\s*(?:m|mn|million|mln)\b', fs_str, re.IGNORECASE)
    if m_match:
        val_str = m_match.group(1).strip()
        if ',' in val_str and '.' in val_str:
            if val_str.find(',') < val_str.find('.'):
                val_str = val_str.replace(',', '')
            else:
                val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            parts = val_str.split(',')
            if len(parts) == 2 and len(parts[1]) == 3:
                val_str = val_str.replace(',', '')
            else:
                val_str = val_str.replace(',', '.')
        try:
            return float(val_str)
        except ValueError:
            pass

    # Thousand match
    k_match = re.search(r'([\d\.,]+)\s*(?:k|thousand)\b', fs_str, re.IGNORECASE)
    if k_match:
        val_str = k_match.group(1).strip().replace(',', '.')
        try:
            return float(val_str) / 1000.0
        except ValueError:
            pass

    # Raw number
    clean_num = re.search(r'([\d\.,]+)', fs_str)
    if clean_num:
        val_str = clean_num.group(1).replace(',', '.')
        try:
            val = float(val_str)
            return val / 1_000_000.0 if val > 1_000_000 else val
        except ValueError:
            pass
    return None


class DelistingRiskRule(BaseAlertRule):
    """Flags ETFs with total assets under management (AUM) below liquidation / delisting threshold."""

    DEFAULT_MIN_AUM_M = 50.0

    @property
    def name(self) -> str:
        return "Delisting Risk"

    @property
    def tag(self) -> str:
        return "#alert/delisting_risk"

    @property
    def description(self) -> str:
        return "ETF AUM / fund size is below minimum viable fund size (default: 50M EUR/USD)."

    def evaluate(self, asset: Asset, context: Any) -> Optional[bool]:
        # Delisting risk applies to ETFs
        if str(asset.asset_type).lower() != "etf" and not asset.fund_size:
            return False

        cfg = context.get_alert_config("delisting_risk", {}) if hasattr(context, "get_alert_config") else {}
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            return False

        min_aum = self.DEFAULT_MIN_AUM_M
        if isinstance(cfg, dict):
            min_aum = float(cfg.get("min_aum_million", self.DEFAULT_MIN_AUM_M))
        elif isinstance(cfg, (int, float)):
            min_aum = float(cfg)

        if not asset.fund_size:
            return None

        parsed_aum = parse_fund_size_to_millions(asset.fund_size)
        if parsed_aum is None:
            return None

        return parsed_aum < min_aum
