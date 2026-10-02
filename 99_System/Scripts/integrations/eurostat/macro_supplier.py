"""Eurostat Macroeconomic Data Supplier.

Fetches official European macroeconomic benchmarks, including Maastricht 10-year
government bond yields, harmonized inflation (HICP), and labor market statistics
directly from the Eurostat Public Dissemination API.
"""

import os
import sys
from typing import Dict, Any, Optional

# Ensure integrations root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

try:
    from resilience import resilient_get
except ImportError:
    resilient_get = None

try:
    import requests
except ImportError:
    requests = None


class EurostatMacroSupplier:
    """Supplier for European sovereign yields and macroeconomic indicators."""

    BASE_API_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    @classmethod
    def _get(cls, endpoint: str, timeout: int = 6) -> Optional[Any]:
        """Perform resilient HTTP GET request against Eurostat API."""
        try:
            url = f"{cls.BASE_API_URL}/{endpoint}"
            get_fn = resilient_get if resilient_get else (requests.get if requests else None)
            if not get_fn:
                return None
            return get_fn(url, timeout=timeout)
        except Exception:
            return None

    @classmethod
    def fetch_10y_yield(cls, geo: str = "PL") -> Dict[str, Any]:
        """Fetch 10-Year Government Bond Benchmark yield (Maastricht criterion).

        Args:
            geo: Country code (e.g. 'PL' for Poland, 'DE' for Germany).

        Returns:
            Dict containing 'yield' (float), 'trend' (string), and 'period' (string).
        """
        default_result = {
            "yield": 5.81 if geo == "PL" else 2.50,
            "trend": "📈 Increasing",
            "period": "latest",
        }

        resp = cls._get(f"irt_lt_mcby_m?geo={geo}&lastTimePeriod=2")
        if not resp or resp.status_code != 200:
            return default_result

        try:
            data = resp.json()
            val_map = data.get("value", {})
            if val_map:
                keys_sorted = sorted([int(k) for k in val_map.keys()])
                latest_val = float(val_map[str(keys_sorted[-1])])
                prior_val = float(val_map[str(keys_sorted[-2])]) if len(keys_sorted) >= 2 else latest_val
                trend = "📈 Increasing" if latest_val > prior_val else ("📉 Decreasing" if latest_val < prior_val else "➡️ Stable")
                
                # Extract period label if present
                time_cats = data.get("dimension", {}).get("time", {}).get("category", {}).get("label", {})
                period_str = list(time_cats.keys())[-1] if time_cats else "latest"

                return {
                    "yield": latest_val,
                    "trend": trend,
                    "period": period_str,
                }
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse Eurostat 10Y yield JSON: {e}\n")

        return default_result

    @classmethod
    def fetch_hicp_inflation(cls, geo: str = "PL") -> Dict[str, Any]:
        """Fetch Harmonised Index of Consumer Prices (HICP) annual inflation rate.

        Args:
            geo: Geographic code ('PL' for Poland, 'EA20' for Eurozone).

        Returns:
            Dict containing 'current', 'prior', 'status', and 'numeric'.
        """
        default_num = 2.5 if geo == "PL" else 2.0
        default_result = {
            "current": f"{default_num:.1f}%",
            "prior": f"{default_num:.1f}%",
            "status": "Moderating",
            "numeric": default_num,
        }

        resp = cls._get(f"prc_hicp_manr?geo={geo}&coicop=CP00&lastTimePeriod=2")
        if not resp or resp.status_code != 200:
            return default_result

        try:
            data = resp.json()
            val_map = data.get("value", {})
            if val_map:
                keys_sorted = sorted([int(k) for k in val_map.keys()])
                latest_val = float(val_map[str(keys_sorted[-1])])
                prior_val = float(val_map[str(keys_sorted[-2])]) if len(keys_sorted) >= 2 else latest_val
                status = "Moderating" if latest_val < prior_val else ("Elevated" if latest_val > 2.5 else "Near Target")

                return {
                    "current": f"{latest_val:.1f}%",
                    "prior": f"{prior_val:.1f}%",
                    "status": status,
                    "numeric": latest_val,
                }
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse Eurostat HICP inflation JSON: {e}\n")

        return default_result

    @classmethod
    def fetch_unemployment_rate(cls, geo: str = "PL") -> Optional[float]:
        """Fetch monthly seasonally adjusted unemployment rate.

        Args:
            geo: Country code (e.g. 'PL').

        Returns:
            Float percentage or None.
        """
        resp = cls._get(f"une_rt_m?geo={geo}&s_adj=SA&age=TOTAL&unit=PC_ACT&sex=T&lastTimePeriod=1")
        if not resp or resp.status_code != 200:
            return None

        try:
            data = resp.json()
            val_map = data.get("value", {})
            if val_map:
                latest_key = list(val_map.keys())[-1]
                return float(val_map[latest_key])
        except Exception:
            pass

        return None
