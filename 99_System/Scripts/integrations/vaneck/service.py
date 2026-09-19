import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger("vaneck_service")

CACHE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../.cache/vaneck_products_cache.json")
)
CACHE_TTL_SECONDS = 86400 * 3  # 3 days

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

EU_SEARCH_URL = "https://www.vaneck.com/Main/FundSearchPanelBlock/GetSearchPanelData"
US_SEARCH_URL = "https://www.vaneck.com/Main/FundListingUs/GetFundData"


def _fetch_eu_products() -> List[Dict[str, Any]]:
    """Fetch European UCITS ETF product catalog from VanEck search panel endpoint."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.vaneck.com/nl/en/",
    }
    params = {"blockId": "281060", "language": "en"}
    try:
        r = requests.get(EU_SEARCH_URL, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            rows = data.get("Rows", [])
            products = []
            for row in rows:
                values = row.get("Values", [])
                name = values[0].strip() if len(values) > 0 and values[0] else None
                isin = values[1].strip().upper() if len(values) > 1 and values[1] else None
                ter = values[2].strip() if len(values) > 2 and values[2] else None
                fund_size = values[3].strip() if len(values) > 3 and values[3] else None
                rel_url = row.get("Url", "").strip()
                keywords = row.get("Keywords", [])

                if not rel_url:
                    continue

                full_url = f"https://www.vaneck.com{rel_url}" if rel_url.startswith("/") else rel_url
                full_url = full_url.replace("https://www.vaneck.com/NL/en/", "https://www.vaneck.com/nl/en/")

                tickers = []
                for kw in keywords:
                    kw_clean = kw.strip().upper()
                    base_t = kw_clean.split()[0]
                    if len(base_t) <= 8 and base_t not in tickers:
                        tickers.append(base_t)

                products.append({
                    "name": name,
                    "isin": isin,
                    "url": full_url,
                    "ter": f"{ter} p.a." if ter and not ter.endswith("p.a.") else ter,
                    "fund_size": fund_size,
                    "tickers": tickers,
                    "region": "EU",
                })
            return products
    except Exception as e:
        logger.debug(f"Failed to fetch European VanEck products: {e}")
    return []


def _fetch_us_products() -> List[Dict[str, Any]]:
    """Fetch US ETF product catalog from VanEck FundListingUs endpoint."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.vaneck.com/us/en/etf-mutual-fund-finder/etfs/",
    }
    payload = {
        "filterJson": json.dumps({
            "InvType": "all",
            "Strategies": [],
            "Funds": [],
            "ShareClass": [],
            "TableType": "search",
            "CurrentPageId": "5517",
        })
    }
    try:
        r = requests.post(US_SEARCH_URL, headers=headers, data=payload, timeout=12)
        if r.status_code == 200:
            data = r.json()
            fund_set = data.get("Result", {}).get("FundSet", [])
            products = []
            for fund in fund_set:
                ticker = fund.get("FundID")
                name = fund.get("FundName")
                rel_url = None
                for row in fund.get("RowData", []):
                    if row.get("Header") == "FundUrl":
                        rel_url = row.get("Value")
                        break
                if not rel_url and not ticker:
                    continue
                full_url = f"https://www.vaneck.com{rel_url}" if rel_url and rel_url.startswith("/") else rel_url
                products.append({
                    "name": name,
                    "isin": None,
                    "url": full_url,
                    "ter": None,
                    "fund_size": None,
                    "tickers": [ticker.strip().upper()] if ticker else [],
                    "region": "US",
                })
            return products
    except Exception as e:
        logger.debug(f"Failed to fetch US VanEck products: {e}")
    return []


def get_vaneck_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """Load cached VanEck product URLs or fetch fresh ones from European and US endpoints."""
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if (time.time() - mtime) < CACHE_TTL_SECONDS:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    eu_products = _fetch_eu_products()
    us_products = _fetch_us_products()
    all_products = eu_products + us_products

    by_isin: Dict[str, Dict[str, Any]] = {}
    by_ticker: Dict[str, Dict[str, Any]] = {}

    for prod in all_products:
        isin = prod.get("isin")
        if isin:
            by_isin[isin.upper()] = prod
        for t in prod.get("tickers", []):
            if t:
                by_ticker[t.upper()] = prod

    catalog = {
        "products": all_products,
        "by_isin": by_isin,
        "by_ticker": by_ticker,
    }

    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to write VanEck cache: {e}")

    return catalog


def fetch_vaneck_url(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None,
) -> Optional[str]:
    """Find the official VanEck product URL dynamically."""
    data = fetch_vaneck_data(ticker=ticker, isin=isin, name=name, yahoo_ticker=yahoo_ticker)
    return data.get("issuer_url") if data else None


def fetch_vaneck_data(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch VanEck product data (official URL, TER, fund size)."""
    catalog = get_vaneck_catalog()
    by_isin = catalog.get("by_isin", {})
    by_ticker = catalog.get("by_ticker", {})
    products = catalog.get("products", [])

    # 1. Match by ISIN (highest accuracy)
    if isin:
        isin_clean = isin.strip().upper()
        if isin_clean in by_isin:
            matched = by_isin[isin_clean]
            return {
                "issuer": "VanEck",
                "issuer_url": matched.get("url"),
                "fund_name": matched.get("name"),
                "ter": matched.get("ter"),
                "fund_size": matched.get("fund_size"),
            }

    # 2. Match by ticker or yahoo_ticker
    tickers_to_check = []
    for t in (ticker, yahoo_ticker):
        if t:
            clean = t.strip().upper()
            tickers_to_check.append(clean)
            base = clean.split(".")[0]
            tickers_to_check.append(base)

    for t in tickers_to_check:
        if t in by_ticker:
            matched = by_ticker[t]
            return {
                "issuer": "VanEck",
                "issuer_url": matched.get("url"),
                "fund_name": matched.get("name"),
                "ter": matched.get("ter"),
                "fund_size": matched.get("fund_size"),
            }

    # 3. Match by name keywords in products
    if name:
        clean_name = name.lower().replace("vaneck", "").replace("ucits", "").replace("etf", "")
        keywords = [w for w in re.findall(r"[a-z0-9]+", clean_name) if len(w) > 2]
        if keywords:
            best_match = None
            best_score = 0
            for prod in products:
                p_name = (prod.get("name") or "").lower()
                p_url = (prod.get("url") or "").lower()
                score = sum(1 for kw in keywords if kw in p_name or kw in p_url)
                if score > best_score and score >= 2:
                    best_score = score
                    best_match = prod

            if best_match:
                return {
                    "issuer": "VanEck",
                    "issuer_url": best_match.get("url"),
                    "fund_name": best_match.get("name"),
                    "ter": best_match.get("ter"),
                    "fund_size": best_match.get("fund_size"),
                }

    return None
