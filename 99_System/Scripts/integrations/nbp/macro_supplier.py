"""NBP Macroeconomic Data Supplier.

Fetches official reference exchange rates, gold fixings, and central bank base rates
directly from the National Bank of Poland (Narodowy Bank Polski) Web APIs and XML feeds.
"""

import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List

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


class NBPMacroSupplier:
    """Supplier for Polish central bank macroeconomic and monetary indicators."""

    NBP_TABLE_A_URL = "https://api.nbp.pl/api/exchangerates/tables/a?format=json"
    NBP_GOLD_URL = "https://api.nbp.pl/api/cenyzlota?format=json"
    NBP_RATES_XML_URL = "https://static.nbp.pl/dane/stopy/stopy_procentowe.xml"

    # 1 troy ounce in grams
    TROY_OUNCE_TO_GRAMS = 31.1034768

    @classmethod
    def _get(cls, url: str, timeout: int = 6) -> Optional[Any]:
        """Perform resilient HTTP GET request."""
        try:
            get_fn = resilient_get if resilient_get else (requests.get if requests else None)
            if not get_fn:
                return None
            return get_fn(url, timeout=timeout)
        except Exception:
            return None

    @classmethod
    def fetch_exchange_rates(cls, target_currencies: Optional[List[str]] = None) -> Dict[str, float]:
        """Fetch official reference exchange rates from NBP Web API (Table A).

        Args:
            target_currencies: Optional list of currency codes (e.g. ['USD', 'EUR', 'GBP']).
                               If None, all currencies in Table A are returned.

        Returns:
            Dict mapping currency codes to mid rates in PLN.
        """
        rates: Dict[str, float] = {}
        resp = cls._get(cls.NBP_TABLE_A_URL)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data and isinstance(data, list) and "rates" in data[0]:
                    for item in data[0]["rates"]:
                        code = item.get("code")
                        mid = item.get("mid")
                        if code and mid:
                            if not target_currencies or code in target_currencies:
                                rates[code] = float(mid)
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse NBP exchange rates JSON: {e}\n")
        return rates

    @classmethod
    def fetch_gold_fixing(cls) -> Optional[Dict[str, Any]]:
        """Fetch official domestic gold price fixing from NBP Web API.

        Returns:
            Dict with 'price_1g_pln', 'price_oz_pln', and 'date', or None on failure.
        """
        resp = cls._get(cls.NBP_GOLD_URL)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    price_1g = float(data[0].get("cena", 0.0))
                    price_oz = price_1g * cls.TROY_OUNCE_TO_GRAMS
                    return {
                        "price_1g_pln": price_1g,
                        "price_oz_pln": price_oz,
                        "date": data[0].get("data", ""),
                    }
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse NBP gold price JSON: {e}\n")
        return None

    @classmethod
    def fetch_base_rates(cls) -> Dict[str, Any]:
        """Fetch official Polish central bank interest rates from NBP XML feed.

        Returns:
            Dict containing reference rate, lombard rate, deposit rate, publication date,
            valid_from date, and trend description in English.
        """
        default_result = {
            "ref_rate": 3.75,
            "lombard_rate": 4.25,
            "deposit_rate": 3.25,
            "trend": "Neutral / Pause",
            "last_decision_date": "2026-03-05",
            "valid_from": "2026-03-05",
        }

        resp = cls._get(cls.NBP_RATES_XML_URL)
        if not resp or resp.status_code != 200:
            return default_result

        try:
            root = ET.fromstring(resp.content)
            pub_date = root.attrib.get("data_publikacji", default_result["last_decision_date"])
            ref_rate = None
            lom_rate = None
            dep_rate = None
            trend_str = "Neutral / Pause"
            valid_from = pub_date

            for pos in root.findall(".//pozycja"):
                pos_id = pos.attrib.get("id")
                rate_val = pos.attrib.get("oprocentowanie", "").replace(",", ".").strip()
                if pos_id == "ref":
                    ref_rate = float(rate_val) if rate_val else default_result["ref_rate"]
                    valid_from = pos.attrib.get("obowiazuje_od", pub_date)
                    raw_trend = pos.attrib.get("trend", "").lower()
                    if "spadek" in raw_trend:
                        trend_str = "Easing / Cut"
                    elif "wzrost" in raw_trend:
                        trend_str = "Hike / Tightening"
                    else:
                        trend_str = "Neutral / Pause"
                elif pos_id == "lom":
                    lom_rate = float(rate_val) if rate_val else default_result["lombard_rate"]
                elif pos_id == "dep":
                    dep_rate = float(rate_val) if rate_val else default_result["deposit_rate"]

            if ref_rate is not None:
                return {
                    "ref_rate": ref_rate,
                    "lombard_rate": lom_rate if lom_rate is not None else (ref_rate + 0.5),
                    "deposit_rate": dep_rate if dep_rate is not None else (ref_rate - 0.5),
                    "trend": trend_str,
                    "last_decision_date": pub_date,
                    "valid_from": valid_from,
                }
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse NBP base rates XML: {e}\n")

        return default_result
