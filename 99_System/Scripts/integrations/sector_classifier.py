import os
import sys
from typing import Dict, Optional, Tuple, Any

# Ensure script directories are accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
for p in (scripts_dir, current_dir):
    if p not in sys.path:
        sys.path.append(p)

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_CONFIG = {
    "dominant_sector": {
        "default_threshold": 50.0,
        "diversified_label": "Diversified",
        "thresholds": {
            "Healthcare": 80.0,
            "Health Care": 80.0,
            "Military": 50.0,
            "Finance": 50.0,
            "Financials": 50.0,
            "Technology": 50.0,
            "Real Estate": 50.0,
        },
        "mappings": {
            "financial_services": "Finance",
            "financials": "Finance",
            "financial services": "Finance",
            "finance": "Finance",
            "insurance - property & casualty": "Finance",
            "insurance - life": "Finance",
            "insurance - specialty": "Finance",
            "insurance": "Finance",
            "banking": "Finance",
            "banks": "Finance",
            "healthcare": "Healthcare",
            "health care": "Healthcare",
            "health_care": "Healthcare",
            "pharmaceuticals": "Healthcare",
            "biotechnology": "Healthcare",
            "military": "Military",
            "defense": "Military",
            "aerospace & defense": "Military",
            "technology": "Technology",
            "information technology": "Technology",
            "tech": "Technology",
            "realestate": "Real Estate",
            "real estate": "Real Estate",
            "reit": "Real Estate",
            "consumer_cyclical": "Consumer Cyclical",
            "consumer discretionary": "Consumer Cyclical",
            "consumer_defensive": "Consumer Defensive",
            "consumer staples": "Consumer Defensive",
            "consumer non-cyclicals": "Consumer Defensive",
            "industrials": "Industrials",
            "industrial": "Industrials",
            "business services": "Industrials",
            "energy": "Energy",
            "oil & gas": "Energy",
            "utilities": "Utilities",
            "basic_materials": "Basic Materials",
            "materials": "Basic Materials",
            "communication_services": "Communication Services",
        }
    }
}


def load_sector_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml with built-in fallbacks."""
    candidate_paths = []
    if config_path:
        candidate_paths.append(config_path)

    workspace_root = os.path.abspath(os.path.join(scripts_dir, "../.."))
    system_dir = os.path.join(workspace_root, "99_System")

    candidate_paths.extend([
        os.path.join(system_dir, "config.yaml"),
        os.path.join(workspace_root, "config.yaml"),
    ])

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if yaml:
                    loaded = yaml.safe_load(content)
                    if isinstance(loaded, dict) and "dominant_sector" in loaded:
                        return loaded
            except Exception:
                pass

    return DEFAULT_CONFIG


def determine_dominant_sector(holdings_data: Optional[Dict[str, float]], config: Optional[Dict[str, Any]] = None) -> str:
    """Determine the dominant sector for an asset/ETF based on sector percentage breakdown.

    Args:
        holdings_data: Dictionary mapping sector names to percentage weights (e.g. {'Financials': 54.93}).
        config: Optional configuration dictionary. If None, loaded automatically via load_sector_config().

    Returns:
        Mapped sector string if a sector exceeds its configured percentage threshold,
        else the configured diversified label (default: "Diversified").
    """
    if not config:
        config = load_sector_config()

    dom_cfg = config.get("dominant_sector", {})
    default_threshold = float(dom_cfg.get("default_threshold", 50.0))
    diversified_label = str(dom_cfg.get("diversified_label", "Diversified"))
    thresholds_map = dom_cfg.get("thresholds", {})
    mappings_map = dom_cfg.get("mappings", {})

    mappings_lower = {k.lower(): v for k, v in mappings_map.items()}
    thresholds_lower = {k.lower(): float(v) for k, v in thresholds_map.items()}

    if not holdings_data or not isinstance(holdings_data, dict):
        return diversified_label

    cleaned_data: Dict[str, float] = {}
    for k, v in holdings_data.items():
        if k is None or v is None:
            continue
        try:
            val = float(v)
            if val > 0:
                cleaned_data[str(k).strip()] = val
        except (ValueError, TypeError):
            continue

    if not cleaned_data:
        return diversified_label

    max_raw_val = max(cleaned_data.values())
    if max_raw_val <= 1.0:
        cleaned_data = {k: v * 100.0 for k, v in cleaned_data.items()}

    aggregated_sectors: Dict[str, float] = {}
    for raw_sector, pct in cleaned_data.items():
        lower_raw = raw_sector.lower()
        mapped_name = mappings_lower.get(lower_raw)
        if not mapped_name:
            mapped_name = raw_sector.title()

        aggregated_sectors[mapped_name] = aggregated_sectors.get(mapped_name, 0.0) + pct

    if not aggregated_sectors:
        return diversified_label

    top_sector, top_pct = max(aggregated_sectors.items(), key=lambda item: item[1])
    sector_threshold = thresholds_lower.get(top_sector.lower(), default_threshold)

    if top_pct >= sector_threshold:
        return top_sector
    else:
        return diversified_label


def fetch_etf_holdings_data(isin: Optional[str], ticker: Optional[str] = None, name: Optional[str] = None) -> Tuple[Dict[str, float], str]:
    """Fetch ETF sector breakdown structure from yfinance or JustETF.

    Returns:
        Tuple of (holdings_dict, source_name).
    """
    holdings: Dict[str, float] = {}
    source = "none"

    if ticker:
        sym = ticker.split('.')[0] if '.' in ticker else ticker
        try:
            import yfinance as yf
            t = yf.Ticker(sym)
            sw = getattr(t, 'funds_data', None) and getattr(t.funds_data, 'sector_weightings', None)
            if sw and isinstance(sw, dict):
                holdings = {k: float(v) for k, v in sw.items() if v is not None}
                source = "yfinance"
        except Exception:
            pass

    if not holdings and isin:
        try:
            from integrations.justetf.service import fetch_justetf_sectors
            justetf_sectors = fetch_justetf_sectors(isin)
            if justetf_sectors:
                holdings = justetf_sectors
                source = "justetf"
        except Exception:
            pass

    return holdings, source
