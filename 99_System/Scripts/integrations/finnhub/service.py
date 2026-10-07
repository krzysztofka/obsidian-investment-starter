import os
import sys
from datetime import datetime, timedelta
from typing import Any

from dotenv import find_dotenv, load_dotenv

# Ensure integrations root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

from resilience import retry_with_backoff

ALERT_INSIDER_SELL_TAG = "#alert/insider_sell"

try:
    import finnhub
except ImportError:
    finnhub = None

try:
    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass


@retry_with_backoff(domain="finnhub.io")
def _safe_finnhub_call(fn, *args, **kwargs):
    """Execute Finnhub SDK method with thread-safe domain rate limiting and retry with backoff."""
    return fn(*args, **kwargs)


def _load_api_key() -> str | None:
    """Load the Finnhub API key from environment variable or .env file."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if api_key:
        return api_key

    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FINNHUB_API_KEY=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip()
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return None


def get_finnhub_client(api_key: str | None = None) -> Any | None:
    """Create and return a Finnhub client instance."""
    if finnhub is None:
        return None
    key = api_key or _load_api_key()
    if not key:
        return None
    try:
        return finnhub.Client(api_key=key)
    except Exception as e:
        sys.stderr.write(f"Finnhub: failed to initialize client: {e}\n")
        return None


def _get_candidate_symbols(symbol: str) -> list[str]:
    """Generate candidate symbols to handle exchange suffixes."""
    candidates = [symbol]
    if "." in symbol:
        parts = symbol.split(".")
        if parts[-1].upper() in ("US", "O", "N", "Q", "ARCA", "BATS", "DE", "LSE", "WA", "XETRA"):
            candidates.insert(0, parts[0])
    return candidates


def fetch_analyst_rating(symbol: str, finnhub_client: Any | None = None) -> str | None:
    """Fetch the latest analyst recommendation consensus from Finnhub."""
    if not symbol:
        return None

    client = finnhub_client or get_finnhub_client()
    if not client:
        return None

    candidate_symbols = _get_candidate_symbols(symbol)
    data = None

    for sym in candidate_symbols:
        try:
            res = _safe_finnhub_call(client.recommendation_trends, sym)
            if res and isinstance(res, list) and len(res) > 0:
                data = res
                break
        except Exception as e:
            sys.stderr.write(f"Finnhub: recommendation_trends failed for {sym}: {e}\n")

    if not data or not isinstance(data, list) or len(data) == 0:
        return None

    latest = data[0]
    strong_buy = latest.get("strongBuy", 0) or 0
    buy = latest.get("buy", 0) or 0
    hold = latest.get("hold", 0) or 0
    sell = latest.get("sell", 0) or 0
    strong_sell = latest.get("strongSell", 0) or 0

    total = strong_buy + buy + hold + sell + strong_sell
    if total == 0:
        return None

    score = (strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1) / total

    if score >= 4.5:
        return "Strong Buy"
    elif score >= 3.5:
        return "Buy"
    elif score >= 2.5:
        return "Hold"
    elif score >= 1.5:
        return "Sell"
    else:
        return "Strong Sell"


def fetch_insider_sentiment(
    symbol: str, from_date: str | None = None, to_date: str | None = None, finnhub_client: Any | None = None
) -> dict[str, Any] | None:
    """Fetch insider sentiment data (MSPR and net share change) for a symbol."""
    if not symbol:
        return None

    client = finnhub_client or get_finnhub_client()
    if not client:
        return None

    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    for sym in _get_candidate_symbols(symbol):
        try:
            res = _safe_finnhub_call(client.stock_insider_sentiment, sym, from_date, to_date)
            if res and isinstance(res, dict) and res.get("data"):
                return res
        except Exception as e:
            sys.stderr.write(f"Finnhub: stock_insider_sentiment failed for {sym}: {e}\n")

    return None


def fetch_insider_transactions(
    symbol: str, from_date: str | None = None, to_date: str | None = None, finnhub_client: Any | None = None
) -> list[dict[str, Any]]:
    """Fetch individual Form 4 insider transactions for a symbol."""
    if not symbol:
        return []

    client = finnhub_client or get_finnhub_client()
    if not client:
        return []

    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    for sym in _get_candidate_symbols(symbol):
        try:
            res = _safe_finnhub_call(client.stock_insider_transactions, sym, from_date, to_date)
            if res and isinstance(res, dict) and res.get("data"):
                return res["data"]
        except Exception as e:
            sys.stderr.write(f"Finnhub: stock_insider_transactions failed for {sym}: {e}\n")

    return []


def check_insider_sell(symbol: str, months: int = 3, finnhub_client: Any | None = None) -> bool:
    """Check if there is net insider selling for the given symbol over the past months."""
    if not symbol:
        return False

    client = finnhub_client or get_finnhub_client()
    if not client:
        return False

    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

    candidate_symbols = _get_candidate_symbols(symbol)

    for sym in candidate_symbols:
        try:
            sent_resp = _safe_finnhub_call(client.stock_insider_sentiment, sym, from_date, to_date)
            data = sent_resp.get("data", []) if isinstance(sent_resp, dict) else []
            if data:
                total_change = sum(item.get("change", 0) for item in data)
                avg_mspr = sum(item.get("mspr", 0) for item in data) / len(data)
                latest = data[-1]
                latest_change = latest.get("change", 0)
                latest_mspr = latest.get("mspr", 0)

                if total_change < 0 or avg_mspr < 0 or latest_change < 0 or latest_mspr < 0:
                    return True
                return False
        except Exception as e:
            sys.stderr.write(f"Finnhub: insider sentiment check error for {sym}: {e}\n")

        try:
            tx_resp = _safe_finnhub_call(client.stock_insider_transactions, sym, from_date, to_date)
            txs = tx_resp.get("data", []) if isinstance(tx_resp, dict) else []
            if txs:
                net_change = sum(item.get("change", 0) for item in txs)
                has_sale = any(item.get("transactionCode") == "S" or item.get("change", 0) < 0 for item in txs)
                if net_change < 0 or has_sale:
                    return True
                return False
        except Exception as e:
            sys.stderr.write(f"Finnhub: insider transactions check error for {sym}: {e}\n")

    return False


def apply_insider_sell_tag(tags: list[str] | str | None, is_insider_sell: bool) -> list[str]:
    """Add or remove '#alert/insider_sell' from a list of tags based on insider selling status."""
    if tags is None:
        result_tags = []
    elif isinstance(tags, (list, tuple)):
        result_tags = [str(t).strip() for t in tags if str(t).strip()]
    elif isinstance(tags, str):
        result_tags = [tags.strip()] if tags.strip() else []
    else:
        result_tags = []

    if is_insider_sell:
        if ALERT_INSIDER_SELL_TAG not in result_tags:
            result_tags.append(ALERT_INSIDER_SELL_TAG)
    else:
        result_tags = [t for t in result_tags if t not in (ALERT_INSIDER_SELL_TAG, "alert/insider_sell")]

    return result_tags
