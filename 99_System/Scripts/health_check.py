#!/usr/bin/env python3
"""Integrations Health Check & Connectivity Diagnostics Engine.

Verifies connectivity, API credentials, endpoints, response latency, and
data availability across external providers used by the Investment Second Brain:
  - Yahoo Finance (yfinance)
  - National Bank of Poland (NBP Table A API)
  - Eurostat (Sovereign Yields API)
  - Stooq (Financial Quotes & Charts)
  - JustETF (ETF Metadata & Scraping)
  - Finnhub (Analyst Consensus & Insider Transactions)
  - Exante (Live REST API & Token Generation)
  - OpenBB (Optional Local Quantitative SDK)
  - ETF Issuers (iShares, Vanguard, VanEck)

Renders real-time diagnostic reports to terminal and updates Health.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# Configure UTF-8 encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure Scripts directory and integrations are in sys.path
SCRIPT_PATH = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(SCRIPT_PATH)
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, "../.."))

for p in (SCRIPTS_DIR, VAULT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# Load environment variables (.env)
try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Default HTTP headers simulating browser client
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class HealthStatus(str, Enum):
    """Health check outcome status."""

    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass
class ProbeResult:
    """Outcome of an individual integration connectivity probe."""

    id: str
    name: str
    category: str
    auth_requirement: str
    status: HealthStatus
    latency_ms: float | None
    endpoint_display: str
    message: str
    troubleshooting: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class HealthReport:
    """Consolidated health report across all probed integrations."""

    timestamp: str
    results: list[ProbeResult]
    total_probed: int
    passed_count: int
    warn_count: int
    failed_count: int
    all_ok: bool
    status_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_probed": self.total_probed,
            "passed_count": self.passed_count,
            "warn_count": self.warn_count,
            "failed_count": self.failed_count,
            "all_ok": self.all_ok,
            "status_summary": self.status_summary,
            "results": [r.to_dict() for r in self.results],
        }


# ==============================================================================
# Helper HTTP session with timeout and retries
# ==============================================================================


def _create_http_session() -> requests.Session:
    """Create a configured requests session with modest connection pooling."""
    session = requests.Session()
    retries = Retry(total=1, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(DEFAULT_HEADERS)
    return session


# ==============================================================================
# Individual Integration Probes
# ==============================================================================


def probe_yfinance(timeout: float = 8.0) -> ProbeResult:
    """Probe Yahoo Finance connectivity via yfinance library."""
    name = "Yahoo Finance"
    category = "Market Data"
    auth = "Public / Free"
    endpoint = "query1.finance.yahoo.com (Ticker: SPY)"

    try:
        import yfinance as yf
    except ImportError:
        return ProbeResult(
            id="yfinance",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=None,
            endpoint_display=endpoint,
            message="yfinance Python package not installed",
            troubleshooting="Run `pip install yfinance` to install the required market data library.",
        )

    t0 = time.perf_counter()
    try:
        ticker = yf.Ticker("SPY")
        # Fast query for current price or 1-day history
        hist = ticker.history(period="1d")
        latency = (time.perf_counter() - t0) * 1000

        if hist is not None and not hist.empty:
            close_price = float(hist["Close"].iloc[-1])
            return ProbeResult(
                id="yfinance",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"Success: retrieved SPY close (${close_price:.2f})",
            )
        else:
            return ProbeResult(
                id="yfinance",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="Query returned empty historical dataset",
                troubleshooting="Yahoo Finance may be rate-limiting queries. Check internet connection or retry in a few moments.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="yfinance",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Request failed: {exc}",
            troubleshooting="Verify internet connectivity and that Yahoo Finance domains (`query1.finance.yahoo.com`) are not blocked.",
        )


def probe_nbp(timeout: float = 8.0) -> ProbeResult:
    """Probe National Bank of Poland (NBP) Table A currency fixing API."""
    name = "National Bank of Poland (NBP)"
    category = "Macro / FX Rates"
    auth = "Public / Free"
    endpoint = "api.nbp.pl/api/exchangerates/tables/a"
    url = f"https://{endpoint}?format=json"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            table_no = data[0].get("no", "Unknown") if isinstance(data, list) and data else "OK"
            return ProbeResult(
                id="nbp",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP 200: Active FX Table A fixing ({table_no})",
            )
        else:
            return ProbeResult(
                id="nbp",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="NBP Web API may be down or experiencing high load. Check `https://api.nbp.pl` in your browser.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="nbp",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check internet connectivity or DNS resolution for `api.nbp.pl`.",
        )


def probe_eurostat(timeout: float = 8.0) -> ProbeResult:
    """Probe Eurostat Public Statistics API for Polish 10Y Sovereign Yields."""
    name = "Eurostat"
    category = "Macro / Sovereign Yields"
    auth = "Public / Free"
    endpoint = "ec.europa.eu/eurostat/api/dissemination (10Y Yield PL)"
    url = (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/irt_lt_mcby_m"
        "?geo=PL&freq=M&sinceTimePeriod=2024-01"
    )

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            has_values = bool(data.get("value"))
            return ProbeResult(
                id="eurostat",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP 200: Valid JSON dataset received ({'data present' if has_values else 'empty'})",
            )
        else:
            return ProbeResult(
                id="eurostat",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Eurostat dissemination API may be undergoing maintenance.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="eurostat",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check network connectivity to European Commission servers (`ec.europa.eu`).",
        )


def probe_stooq(timeout: float = 8.0) -> ProbeResult:
    """Probe Stooq quote & chart service accessibility."""
    name = "Stooq"
    category = "Market Quotes & Charts"
    auth = "Public / Free"
    endpoint = "stooq.pl/q/d/l/?s=aapl.us&i=d"
    url = f"https://{endpoint}"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200 and ("Date" in resp.text or "Data" in resp.text or "," in resp.text):
            return ProbeResult(
                id="stooq",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="HTTP 200: CSV quote data stream accessible",
            )
        elif resp.status_code == 200:
            return ProbeResult(
                id="stooq",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="HTTP 200: Service reachable",
            )
        else:
            return ProbeResult(
                id="stooq",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Stooq may require a valid User-Agent header or have temporarily throttled requests.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="stooq",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Verify internet connectivity to `stooq.pl`.",
        )


def probe_justetf(timeout: float = 8.0) -> ProbeResult:
    """Probe JustETF website and scraping accessibility."""
    name = "JustETF"
    category = "ETF Metadata & Scraper"
    auth = "Public / Free"
    endpoint = "justetf.com/en/etf-profile.html (ISIN: IE00B4L5Y983)"
    url = "https://www.justetf.com/en/etf-profile.html?isin=IE00B4L5Y983"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            has_content = "iShares" in resp.text or "ETF" in resp.text or "Core MSCI World" in resp.text
            return ProbeResult(
                id="justetf",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP 200: Profile page reachable ({'ETF metadata detected' if has_content else 'ok'})",
            )
        elif resp.status_code in (403, 429):
            return ProbeResult(
                id="justetf",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.WARN,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code} (Rate limited / Bot detection)",
                troubleshooting="JustETF has strict Cloudflare bot detection. Requests use automatic throttling, but frequent checks may be temporarily blocked.",
            )
        else:
            return ProbeResult(
                id="justetf",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="JustETF is returning non-200 status. Check `https://www.justetf.com` in your browser.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="justetf",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check network connectivity or DNS resolution for `www.justetf.com`.",
        )


def _is_placeholder_or_empty(val: str | None) -> bool:
    """Check if an environment credential is blank, unset, or a template placeholder."""
    if not val:
        return True
    v = val.strip().lower()
    return (
        not v
        or v.startswith("your_")
        or "placeholder" in v
        or "example" in v
        or v in ("none", "null", "test_key", "dummy")
    )


# Pre-import integration modules safely in main thread to avoid multithreading import deadlocks
try:
    from integrations.openbb.service import is_openbb_available  # noqa: F401
except Exception:
    pass

try:
    from integrations.finnhub.service import _load_api_key  # noqa: F401
except Exception:
    pass

try:
    from integrations.exante.service import ExanteClient  # noqa: F401
except Exception:
    pass


def probe_finnhub(timeout: float = 8.0) -> ProbeResult:
    """Probe Finnhub API credentials and recommendation consensus endpoint."""
    name = "Finnhub"
    category = "Market Intelligence / SEC"
    auth = "API Key in .env (`FINNHUB_API_KEY`)"
    endpoint = "finnhub.io/api/v1/stock/recommendation (AAPL)"

    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not api_key:
        try:
            from integrations.finnhub.service import _load_api_key

            api_key = _load_api_key() or ""
        except Exception:
            pass

    if _is_placeholder_or_empty(api_key):
        return ProbeResult(
            id="finnhub",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.WARN,
            latency_ms=None,
            endpoint_display="finnhub.io",
            message="FINNHUB_API_KEY not configured (placeholder detected in .env)",
            troubleshooting="Register for a free key at https://finnhub.io and set `FINNHUB_API_KEY=your_key` in `.env` to enable analyst ratings and SEC insider trading alerts.",
        )

    url = f"https://finnhub.io/api/v1/stock/recommendation?symbol=AAPL&token={api_key}"
    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            return ProbeResult(
                id="finnhub",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP 200: API key verified, {len(data) if isinstance(data, list) else 0} consensus records received",
            )
        elif resp.status_code in (401, 403):
            return ProbeResult(
                id="finnhub",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP {resp.status_code}: Invalid or unauthorized API key",
                troubleshooting="Verify that `FINNHUB_API_KEY` in `.env` is correct and active at https://finnhub.io/dashboard.",
            )
        elif resp.status_code == 429:
            return ProbeResult(
                id="finnhub",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.WARN,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="HTTP 429: Rate limit exceeded (60 req/min free tier)",
                troubleshooting="Finnhub free tier is limited to 60 req/min. The vault automatically throttles requests, but wait a minute before re-testing.",
            )
        else:
            return ProbeResult(
                id="finnhub",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Check Finnhub service status.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="finnhub",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check network connectivity to `finnhub.io`.",
        )


def probe_exante(timeout: float = 8.0) -> ProbeResult:
    """Probe Exante REST API credentials and account summary connectivity."""
    name = "Exante REST API"
    category = "Broker API"
    auth = "API Key & Secret in .env"
    endpoint = "api-live.exante.eu/md/3.0/summary"

    api_key = (
        os.environ.get("EXANTE_API_KEY")
        or os.environ.get("EXANTE_APPLICATION_ID")
        or os.environ.get("EXANTE_CLIENT_ID")
        or ""
    ).strip()
    api_secret = (
        os.environ.get("EXANTE_API_SECRET")
        or os.environ.get("EXANTE_SHARED_KEY")
        or os.environ.get("EXANTE_SECRET_KEY")
        or ""
    ).strip()

    if _is_placeholder_or_empty(api_key) or _is_placeholder_or_empty(api_secret):
        return ProbeResult(
            id="exante",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.WARN,
            latency_ms=None,
            endpoint_display="api-live.exante.eu",
            message="EXANTE credentials not configured (placeholder detected in .env)",
            troubleshooting="To enable live broker synchronization without manual CSVs, generate API credentials in Exante Client Area and set `EXANTE_API_KEY` and `EXANTE_API_SECRET` in `.env`.",
        )

    t0 = time.perf_counter()
    try:
        from integrations.exante.service import ExanteClient

        client = ExanteClient(api_key=api_key, api_secret=api_secret)
        accounts = client.get_accounts()
        latency = (time.perf_counter() - t0) * 1000

        if accounts:
            return ProbeResult(
                id="exante",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"Success: connected and retrieved {len(accounts)} account(s)",
            )
        else:
            return ProbeResult(
                id="exante",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="Success: API authenticated (zero active accounts returned)",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        msg = str(exc)
        is_auth = "401" in msg or "403" in msg or "auth" in msg.lower() or "invalid" in msg.lower()
        return ProbeResult(
            id="exante",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"{'Authentication failed: ' if is_auth else 'API error: '}{msg}",
            troubleshooting="Verify that `EXANTE_API_KEY` and `EXANTE_API_SECRET` in `.env` are valid for your Exante environment (Live vs Demo).",
        )


def probe_openbb(timeout: float = 8.0) -> ProbeResult:
    """Probe OpenBB local library availability."""
    name = "OpenBB Platform"
    category = "Local Quantitative SDK"
    auth = "Optional Python Library"
    endpoint = "openbb python package"

    t0 = time.perf_counter()
    try:
        from integrations.openbb.service import is_openbb_available

        available = is_openbb_available()
        latency = (time.perf_counter() - t0) * 1000

        if available:
            return ProbeResult(
                id="openbb",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="OpenBB SDK loaded and operational",
            )
        else:
            return ProbeResult(
                id="openbb",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.WARN,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="OpenBB package not installed (optional, yfinance fallback active)",
                troubleshooting="OpenBB is optional. The vault automatically falls back to Yahoo Finance for fundamental metrics. To install, run: `pip install openbb`.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="openbb",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.WARN,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"OpenBB check warning: {exc}",
            troubleshooting="OpenBB is optional; yfinance fallback is active.",
        )


def probe_ishares(timeout: float = 8.0) -> ProbeResult:
    """Probe BlackRock / iShares product catalog and web service."""
    name = "iShares (BlackRock)"
    category = "ETF Issuer Scraper"
    auth = "Public / Free"
    endpoint = "ishares.com/uk (Core MSCI World)"
    url = "https://www.ishares.com/uk/individual/en/products/251882/ishares-core-msci-world-ucits-etf-acc-fund"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            return ProbeResult(
                id="ishares",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message="HTTP 200: iShares fund portal reachable",
            )
        else:
            return ProbeResult(
                id="ishares",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Check accessibility of `https://www.ishares.com` in your browser.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="ishares",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check internet connectivity to `ishares.com`.",
        )


def probe_vanguard(timeout: float = 8.0) -> ProbeResult:
    """Probe Vanguard ETF portal reachability."""
    name = "Vanguard"
    category = "ETF Issuer Scraper"
    auth = "Public / Free"
    endpoint = "vanguardinvestor.co.uk"
    url = "https://www.vanguardinvestor.co.uk/"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code in (200, 301, 302):
            return ProbeResult(
                id="vanguard",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP {resp.status_code}: Vanguard portal reachable",
            )
        else:
            return ProbeResult(
                id="vanguard",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Check accessibility of `https://www.vanguardinvestor.co.uk`.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="vanguard",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check internet connectivity to `vanguardinvestor.co.uk`.",
        )


def probe_vaneck(timeout: float = 8.0) -> ProbeResult:
    """Probe VanEck Europe ETF portal reachability."""
    name = "VanEck"
    category = "ETF Issuer Scraper"
    auth = "Public / Free"
    endpoint = "vaneck.com/nl/en/etf/equity/tdiv/overview/"
    url = "https://www.vaneck.com/nl/en/etf/equity/tdiv/overview/"

    session = _create_http_session()
    t0 = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code in (200, 301, 302):
            return ProbeResult(
                id="vaneck",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.OK,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP {resp.status_code}: VanEck portal reachable",
            )
        else:
            return ProbeResult(
                id="vaneck",
                name=name,
                category=category,
                auth_requirement=auth,
                status=HealthStatus.FAIL,
                latency_ms=latency,
                endpoint_display=endpoint,
                message=f"HTTP status {resp.status_code}",
                troubleshooting="Check accessibility of `https://www.vaneck.com`.",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ProbeResult(
            id="vaneck",
            name=name,
            category=category,
            auth_requirement=auth,
            status=HealthStatus.FAIL,
            latency_ms=latency,
            endpoint_display=endpoint,
            message=f"Connection error: {exc}",
            troubleshooting="Check internet connectivity to `vaneck.com`.",
        )


# Registry of all probe functions
PROBES: dict[str, Callable[[float], ProbeResult]] = {
    "yfinance": probe_yfinance,
    "nbp": probe_nbp,
    "eurostat": probe_eurostat,
    "stooq": probe_stooq,
    "justetf": probe_justetf,
    "finnhub": probe_finnhub,
    "exante": probe_exante,
    "openbb": probe_openbb,
    "ishares": probe_ishares,
    "vanguard": probe_vanguard,
    "vaneck": probe_vaneck,
}


# ==============================================================================
# Execution & Report Generation Engine
# ==============================================================================


def run_probes(
    selected_ids: list[str] | None = None,
    timeout: float = 8.0,
    max_workers: int = 6,
) -> HealthReport:
    """Execute probes concurrently and compile a structured HealthReport."""
    probe_map = PROBES
    if selected_ids:
        probe_map = {pid: fn for pid, fn in PROBES.items() if pid.lower() in [s.lower() for s in selected_ids]}

    results_dict: dict[str, ProbeResult] = {}

    with ThreadPoolExecutor(max_workers=min(max_workers, len(probe_map) or 1)) as executor:
        future_to_id = {executor.submit(fn, timeout): pid for pid, fn in probe_map.items()}
        for future in as_completed(future_to_id):
            pid = future_to_id[future]
            try:
                res = future.result()
                results_dict[pid] = res
            except Exception as e:
                results_dict[pid] = ProbeResult(
                    id=pid,
                    name=pid,
                    category="Unknown",
                    auth_requirement="Unknown",
                    status=HealthStatus.FAIL,
                    latency_ms=None,
                    endpoint_display="N/A",
                    message=f"Unhandled probe error: {e}",
                    troubleshooting="Unexpected exception during probe execution.",
                )

    # Maintain original definition order
    ordered_results = [results_dict[pid] for pid in probe_map.keys() if pid in results_dict]

    passed = sum(1 for r in ordered_results if r.status == HealthStatus.OK)
    warn = sum(1 for r in ordered_results if r.status == HealthStatus.WARN)
    failed = sum(1 for r in ordered_results if r.status == HealthStatus.FAIL)
    total = len(ordered_results)

    status_summary = f"{passed}/{total} Passed"
    if warn > 0:
        status_summary += f", {warn} Warnings"
    if failed > 0:
        status_summary += f", {failed} Failed"

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return HealthReport(
        timestamp=now_iso,
        results=ordered_results,
        total_probed=total,
        passed_count=passed,
        warn_count=warn,
        failed_count=failed,
        all_ok=(failed == 0),
        status_summary=status_summary,
    )


def render_health_markdown(
    report: HealthReport,
    target_vault: str | None = None,
    template_path: str | None = None,
) -> str:
    """Render the Jinja2 health_template.md with report data."""
    vault = os.path.abspath(target_vault or VAULT_ROOT)
    t_path = template_path or os.path.join(vault, "99_System", "Templates", "health_template.md")

    if not os.path.exists(t_path):
        raise FileNotFoundError(f"Health template not found at {t_path}")

    with open(t_path, encoding="utf-8") as f:
        template_str = f.read()

    from jinja2 import Template

    template = Template(template_str)

    rendered = template.render(
        last_checked=report.timestamp,
        status_summary=report.status_summary,
        total_probed=report.total_probed,
        passed_count=report.passed_count,
        warn_count=report.warn_count,
        failed_count=report.failed_count,
        all_ok=report.all_ok,
        results=report.results,
    )

    return rendered


def update_health_markdown_file(
    report: HealthReport,
    target_vault: str | None = None,
) -> str:
    """Render template and write Health.md to target vault root."""
    vault = os.path.abspath(target_vault or VAULT_ROOT)
    md_content = render_health_markdown(report, target_vault=vault)
    target_file = os.path.join(vault, "Health.md")

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    return target_file


# ==============================================================================
# CLI Display Formatting
# ==============================================================================


def print_cli_report(report: HealthReport) -> None:
    """Print visually polished terminal diagnostic table using Rich or ASCII."""
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print()
        console.rule("[bold cyan]🩺 Integrations Health & Connectivity Diagnostics[/bold cyan]")
        console.print(f"[dim]Timestamp: {report.timestamp} | Probed: {report.total_probed} services[/dim]\n")

        table = Table(box=box.ROUNDED, show_lines=True)
        table.add_column("Service", style="bold white", min_width=20)
        table.add_column("Category", style="dim", min_width=15)
        table.add_column("Status", justify="center", min_width=10)
        table.add_column("Latency", justify="right", min_width=10)
        table.add_column("Probe Endpoint", style="dim", min_width=25)
        table.add_column("Details", min_width=30)

        for r in report.results:
            if r.status == HealthStatus.OK:
                status_badge = "[bold green]✅ OK[/bold green]"
            elif r.status == HealthStatus.WARN:
                status_badge = "[bold yellow]⚠️ WARN[/bold yellow]"
            elif r.status == HealthStatus.FAIL:
                status_badge = "[bold red]❌ FAIL[/bold red]"
            else:
                status_badge = f"[dim]{r.status.value}[/dim]"

            latency_str = f"{r.latency_ms:.0f} ms" if r.latency_ms is not None else "—"

            table.add_row(
                r.name,
                r.category,
                status_badge,
                latency_str,
                r.endpoint_display,
                r.message,
            )

        console.print(table)

        # Summary box
        if report.failed_count > 0:
            console.print(
                f"\n[bold red]❌ {report.failed_count} service(s) failed connectivity checks.[/bold red] "
                f"[yellow]({report.warn_count} warnings, {report.passed_count} passed)[/yellow]"
            )
        elif report.warn_count > 0:
            console.print(
                f"\n[bold yellow]⚠️ {report.passed_count}/{report.total_probed} services operational[/bold yellow] "
                f"[dim]({report.warn_count} warnings for optional/unconfigured integrations)[/dim]"
            )
        else:
            console.print(
                f"\n[bold green]✅ All {report.passed_count} integrations are healthy and operational![/bold green]"
            )

        # Actionable hints for failed or warned items
        needs_attention = [r for r in report.results if r.status in (HealthStatus.FAIL, HealthStatus.WARN)]
        if needs_attention:
            console.print("\n[bold]🛠️ Remediation & Hints:[/bold]")
            for r in needs_attention:
                prefix = "[bold red]FAIL[/bold red]" if r.status == HealthStatus.FAIL else "[yellow]WARN[/yellow]"
                console.print(f"  • {prefix} [bold]{r.name}[/bold]: {r.troubleshooting}")
        console.print()

    except ImportError:
        # Fallback to plain ASCII table if rich is unavailable
        print("\n" + "=" * 78)
        print("🩺 INTEGRATIONS HEALTH & CONNECTIVITY DIAGNOSTICS")
        print(f"Timestamp: {report.timestamp} | Status: {report.status_summary}")
        print("=" * 78)
        print(f"{'Service':<22} {'Status':<10} {'Latency':<10} {'Details'}")
        print("-" * 78)
        for r in report.results:
            lat = f"{r.latency_ms:.0f} ms" if r.latency_ms is not None else "—"
            print(f"{r.name:<22} {r.status.value:<10} {lat:<10} {r.message}")
        print("=" * 78)


# ==============================================================================
# Public runner function
# ==============================================================================


def run_health_check(
    selected_integrations: list[str] | None = None,
    write_markdown: bool = True,
    target_vault: str | None = None,
    timeout: float = 8.0,
    as_json: bool = False,
) -> tuple[HealthReport, int]:
    """Execute health check, update Health.md, and return (report, exit_code).

    Returns:
        Tuple of (HealthReport, exit_code), where exit_code is 0 if all configured
        services pass, or 1 if any service failed.
    """
    report = run_probes(selected_ids=selected_integrations, timeout=timeout)

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_cli_report(report)

    if write_markdown:
        try:
            target_path = update_health_markdown_file(report, target_vault=target_vault)
            if not as_json:
                print(f"📝 Health dashboard updated: {target_path}")
        except Exception as e:
            if not as_json:
                print(f"⚠️ Warning: Failed to write Health.md: {e}")

    # Exit 0 if all pass / only warnings; exit 1 if any hard FAIL
    exit_code = 0 if report.all_ok else 1
    return report, exit_code


# ==============================================================================
# CLI Entrypoint
# ==============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Integrations Health Check & Connectivity Diagnostics for Investment Second Brain.",
    )
    parser.add_argument(
        "-i",
        "--integration",
        dest="integration",
        type=str,
        default=None,
        help="Check only a specific integration (e.g. 'yfinance', 'finnhub', 'exante', 'nbp').",
    )
    parser.add_argument(
        "--no-md",
        action="store_true",
        help="Do not write/update Health.md in vault root.",
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        type=str,
        default=None,
        help="Target vault root directory. Defaults to current vault root.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="Network probe timeout in seconds (default: 8.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON format to stdout.",
    )

    args = parser.parse_args()

    selected = [args.integration] if args.integration else None
    _, exit_code = run_health_check(
        selected_integrations=selected,
        write_markdown=not args.no_md,
        target_vault=args.target,
        timeout=args.timeout,
        as_json=args.json,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
