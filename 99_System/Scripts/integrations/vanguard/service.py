import os
import sys
import re
import json
import logging
from typing import Dict, Any, Optional, List

# Ensure integrations root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

from resilience import resilient_get

logger = logging.getLogger("vanguard_service")

CACHE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../.cache/vanguard_products_cache.json")
)
CACHE_TTL_SECONDS = 86400 * 3  # 3 days

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _fetch_uk_sitemap_urls() -> List[str]:
    """Fetch investment URLs dynamically from Vanguard UK sitemap."""
    try:
        r = resilient_get(
            "https://www.vanguardinvestor.co.uk/sitemap.xml",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r.status_code == 200:
            urls = re.findall(
                r"<loc>(https://www\.vanguardinvestor\.co\.uk/investments/[^<]+)</loc>",
                r.text,
            )
            return sorted(list(set(urls)))
    except Exception as e:
        logger.debug(f"Failed to fetch Vanguard UK sitemap: {e}")
    return []


def get_vanguard_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """Load cached Vanguard product URLs or fetch fresh ones."""
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            import time
            if (time.time() - mtime) < CACHE_TTL_SECONDS:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    sitemap_urls = _fetch_uk_sitemap_urls()
    catalog = {
        "sitemap_urls": sitemap_urls,
    }

    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to write Vanguard cache: {e}")

    return catalog


def _check_us_vanguard_url(ticker_symbol: str) -> Optional[str]:
    """Check if ticker corresponds to a US Vanguard ETF profile."""
    cleaned = ticker_symbol.split(".")[0].strip().lower()
    if not cleaned or len(cleaned) > 5:
        return None
    url = f"https://investor.vanguard.com/investment-products/etfs/profile/{cleaned}"
    try:
        r = resilient_get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
        if r.status_code == 200:
            return url
    except Exception:
        pass
    return None


def fetch_vanguard_url(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None,
) -> Optional[str]:
    """Find the official Vanguard product URL dynamically (US profile or European sitemap)."""
    # 1. Check US Vanguard ETF profiles (e.g. VTV, VOO, VTI, BND, VXUS)
    for t in (yahoo_ticker, ticker):
        if t:
            us_url = _check_us_vanguard_url(t)
            if us_url:
                return us_url

    # 2. Dynamic match against UK sitemap URLs using name keywords
    catalog = get_vanguard_catalog()
    sitemap_urls = catalog.get("sitemap_urls", [])
    if sitemap_urls and name:
        clean_name = name.lower()
        clean_name = clean_name.replace("vngrd", "").replace("vanguard", "")
        keywords = [w for w in re.findall(r"[a-z0-9]+", clean_name) if len(w) > 2 and w not in ["etf", "ucits", "shares"]]

        best_match = None
        best_score = 0
        for u in sitemap_urls:
            slug = u.split("/investments/")[-1].lower()
            score = sum(1 for kw in keywords if kw in slug)
            if score > best_score and score >= 2:
                best_score = score
                best_match = u

        if best_match:
            return best_match

    return None


def fetch_vanguard_data(
    ticker: Optional[str] = None,
    isin: Optional[str] = None,
    name: Optional[str] = None,
    yahoo_ticker: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch Vanguard product data and profile URL."""
    url = fetch_vanguard_url(ticker=ticker, isin=isin, name=name, yahoo_ticker=yahoo_ticker)
    if not url:
        return None

    return {
        "issuer": "Vanguard",
        "issuer_url": url,
    }
