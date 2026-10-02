import os
import sys
import re
import json
import time
from typing import Optional, Dict, Any, Tuple, List

# Ensure integrations root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

from resilience import resilient_get

# Cache file location and TTL (24 hours)
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "ishares_products_cache.json")
CACHE_TTL_SECONDS = 86400  # 24 hours

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
}

US_SCREENER_URL = "https://www.ishares.com/us/product-screener/product-screener-v3.jsn?dcrPath=/templatedata/config/product-screener-v3/data/en/us-ishares/product-screener-ketto"
UK_SCREENER_URL = "https://www.ishares.com/varnish-api/blk-product-screener-server/api/v1/product-screener/product-data"
UK_SCREENER_PARAMS = {
    'country': 'gb',
    'language': 'en',
    'siteName': 'ishares-uk',
    'userType': 'individual',
}

_memory_cache: Optional[Dict[str, Any]] = None


def _load_disk_cache() -> Optional[Dict[str, Any]]:
    """Load cached products from disk if valid and not expired."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        timestamp = cached.get('timestamp', 0)
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return cached.get('data')
    except Exception:
        pass
    return None


def _save_disk_cache(data: Dict[str, Any]) -> None:
    """Save products data to disk cache with current timestamp."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time(), 'data': data}, f)
    except Exception:
        pass


def _fetch_us_products() -> Dict[str, Dict[str, Any]]:
    """Fetch and parse US iShares product catalog."""
    products_by_ticker = {}
    try:
        resp = resilient_get(US_SCREENER_URL, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            json_data = resp.json()
            table_data = json_data.get('data', {}).get('tableData', {})
            columns = [col.get('name') for col in table_data.get('columns', [])]
            data_rows = table_data.get('data', [])

            ticker_idx = columns.index('localExchangeTicker') if 'localExchangeTicker' in columns else -1
            url_idx = columns.index('productPageUrl') if 'productPageUrl' in columns else -1
            name_idx = columns.index('fundName') if 'fundName' in columns else -1
            ter_idx = columns.index('ter') if 'ter' in columns else -1
            net_assets_idx = columns.index('totalNetAssets') if 'totalNetAssets' in columns else -1

            if ticker_idx >= 0 and url_idx >= 0:
                for row in data_rows:
                    ticker = row[ticker_idx]
                    raw_url = row[url_idx]
                    if not ticker or not raw_url:
                        continue
                    full_url = f"https://www.ishares.com{raw_url}" if raw_url.startswith('/') else raw_url
                    fund_name = row[name_idx] if name_idx >= 0 else None

                    ter = None
                    if ter_idx >= 0 and row[ter_idx]:
                        t_val = row[ter_idx]
                        ter = f"{t_val.get('d', '')}% p.a." if isinstance(t_val, dict) else f"{t_val}% p.a."

                    fund_size = None
                    if net_assets_idx >= 0 and row[net_assets_idx]:
                        na_val = row[net_assets_idx]
                        fund_size = na_val.get('d') if isinstance(na_val, dict) else str(na_val)

                    prod_info = {
                        'issuer_url': full_url,
                        'fund_name': fund_name,
                        'ticker': ticker,
                        'region': 'US',
                        'ter': ter,
                        'fund_size': fund_size,
                    }
                    products_by_ticker[ticker.strip().upper()] = prod_info
    except Exception as e:
        print(f"Warning: Failed to fetch US iShares products: {e}")

    return products_by_ticker


def _fetch_uk_products() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Fetch and parse UK/European iShares product catalog."""
    by_isin: Dict[str, Dict[str, Any]] = {}
    by_ticker: Dict[str, Dict[str, Any]] = {}

    try:
        resp = resilient_get(UK_SCREENER_URL, params=UK_SCREENER_PARAMS, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            catalog = resp.json()
            for _, item in catalog.items():
                if not isinstance(item, dict):
                    continue
                raw_url = item.get('productPageUrl')
                if not raw_url:
                    continue
                full_url = f"https://www.ishares.com{raw_url}" if raw_url.startswith('/') else raw_url

                isin = item.get('isin')
                ticker = item.get('localExchangeTicker')
                fund_name = item.get('fundName')
                domicile = item.get('domicile')
                use_of_profits = item.get('useOfProfits')

                ter = None
                ter_val = item.get('ter')
                if ter_val:
                    ter_d = ter_val.get('d') if isinstance(ter_val, dict) else str(ter_val)
                    if ter_d and ter_d != '-':
                        ter = f"{ter_d}% p.a."

                fund_size = None
                fs_val = item.get('totalFundSizeInMillions')
                if fs_val:
                    fs_d = fs_val.get('d') if isinstance(fs_val, dict) else str(fs_val)
                    if fs_d and fs_d != '-':
                        fund_size = f"{fs_d}m"

                prod_info = {
                    'issuer_url': full_url,
                    'fund_name': fund_name,
                    'ticker': ticker,
                    'isin': isin,
                    'region': 'UK',
                    'ter': ter,
                    'fund_size': fund_size,
                    'domicile': domicile,
                    'distribution_policy': use_of_profits,
                }

                if isin:
                    by_isin[isin.strip().upper()] = prod_info
                if ticker:
                    by_ticker[ticker.strip().upper()] = prod_info
    except Exception as e:
        print(f"Warning: Failed to fetch UK iShares products: {e}")

    return by_isin, by_ticker


def get_ishares_catalog() -> Dict[str, Any]:
    """Retrieve full cached or freshly fetched iShares product catalog."""
    global _memory_cache
    if _memory_cache is not None:
        return _memory_cache

    disk_data = _load_disk_cache()
    if disk_data is not None:
        _memory_cache = disk_data
        return _memory_cache

    us_by_ticker = _fetch_us_products()
    uk_by_isin, uk_by_ticker = _fetch_uk_products()

    data = {
        'us_by_ticker': us_by_ticker,
        'uk_by_isin': uk_by_isin,
        'uk_by_ticker': uk_by_ticker,
    }
    _save_disk_cache(data)
    _memory_cache = data
    return _memory_cache


def _extract_ticker_candidates(ticker: Optional[str], yahoo_ticker: Optional[str]) -> List[str]:
    """Extract candidate clean tickers for lookup, removing exchange suffixes."""
    candidates = []
    for raw in [ticker, yahoo_ticker]:
        if not raw:
            continue
        cleaned = raw.strip().upper()
        if not cleaned:
            continue
        if cleaned not in candidates:
            candidates.append(cleaned)
        # Strip exchange suffix (e.g., .ARCA, .LSE, .L, .DE, .SG, .WA)
        if '.' in cleaned:
            base = cleaned.split('.')[0]
            if base and base not in candidates:
                candidates.append(base)
    return candidates


def fetch_ishares_data(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Lookup iShares product data by ISIN, ticker, or Yahoo ticker."""
    catalog = get_ishares_catalog()
    uk_by_isin = catalog.get('uk_by_isin', {})
    us_by_ticker = catalog.get('us_by_ticker', {})
    uk_by_ticker = catalog.get('uk_by_ticker', {})

    # 1. Match by ISIN in UK/European catalog
    if isin:
        clean_isin = isin.strip().upper()
        if clean_isin in uk_by_isin:
            return uk_by_isin[clean_isin]

    # Also check if ticker looks like an ISIN
    if ticker and len(ticker) == 12 and ticker[:2].isalpha():
        clean_isin = ticker.strip().upper()
        if clean_isin in uk_by_isin:
            return uk_by_isin[clean_isin]

    # 2. Match by clean ticker in US catalog
    candidates = _extract_ticker_candidates(ticker, yahoo_ticker)
    for cand in candidates:
        if cand in us_by_ticker:
            return us_by_ticker[cand]

    # 3. Match by clean ticker in UK/European catalog
    for cand in candidates:
        if cand in uk_by_ticker:
            return uk_by_ticker[cand]

    # 4. Optional fallback: match by fund name if clearly an iShares fund
    if name:
        name_lower = name.lower()
        if 'ishares' in name_lower:
            # Check US products
            for prod in us_by_ticker.values():
                fn = (prod.get('fund_name') or '').lower()
                if fn and fn == name_lower:
                    return prod
            # Check UK products
            for prod in uk_by_isin.values():
                fn = (prod.get('fund_name') or '').lower()
                if fn and fn == name_lower:
                    return prod

    return None


def fetch_ishares_url(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None
) -> Optional[str]:
    """Retrieve official iShares product URL."""
    data = fetch_ishares_data(ticker=ticker, isin=isin, name=name, yahoo_ticker=yahoo_ticker)
    if data and data.get('issuer_url'):
        return data['issuer_url']
    return None
