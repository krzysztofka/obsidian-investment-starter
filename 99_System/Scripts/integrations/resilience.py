import os
import sys
import time
import random
import threading
import urllib.parse
from typing import Optional, Dict, Any, Callable, TypeVar, Tuple, Type, Union
from functools import wraps
import requests
from requests.adapters import HTTPAdapter

try:
    import yaml
except ImportError:
    yaml = None

# Ensure script root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
vault_root = os.path.dirname(scripts_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

F = TypeVar('F', bound=Callable[..., Any])

# Default resilience configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 0.5
DEFAULT_MAX_DELAY = 10.0
DEFAULT_JITTER = True
DEFAULT_RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)

DEFAULT_RATE_LIMITS = {
    'finnhub.io': 10.0,
    'query1.finance.yahoo.com': 15.0,
    'query2.finance.yahoo.com': 15.0,
    'justetf.com': 5.0,
    'stooq.com': 8.0,
    'stooq.pl': 8.0,
    'ishares.com': 6.0,
    'vanguard.com': 6.0,
    'vanguard.co.uk': 6.0,
    'vaneck.com': 6.0,
    'api.nbp.pl': 10.0,
}


def load_resilience_config(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load resilience configuration from config.yaml via Pydantic VaultConfig."""
    try:
        from model.config import load_vault_config
        cfg = load_vault_config(base_dir=base_dir)
        return cfg.resilience.model_dump()
    except Exception:
        return {
            "max_retries": DEFAULT_MAX_RETRIES,
            "base_delay_seconds": DEFAULT_BASE_DELAY,
            "max_delay_seconds": DEFAULT_MAX_DELAY,
            "jitter": DEFAULT_JITTER,
            "rate_limits": DEFAULT_RATE_LIMITS,
        }


class DomainRateLimiter:
    """Thread-safe Token Bucket / Rate Limiter per network domain."""

    def __init__(self, rate_limits: Optional[Dict[str, float]] = None):
        self._lock = threading.Lock()
        self._rate_limits = dict(rate_limits or DEFAULT_RATE_LIMITS)
        # state per domain: (last_timestamp, current_tokens)
        self._state: Dict[str, Tuple[float, float]] = {}

    def extract_domain(self, url_or_domain: str) -> str:
        """Extract clean hostname from URL or return domain name directly."""
        if "://" in url_or_domain:
            try:
                parsed = urllib.parse.urlparse(url_or_domain)
                return (parsed.hostname or url_or_domain).lower()
            except Exception:
                return url_or_domain.lower()
        return url_or_domain.lower()

    def get_domain_rate(self, domain: str) -> float:
        """Get allowed requests per second for domain."""
        domain_lower = domain.lower()
        with self._lock:
            for key, rate in self._rate_limits.items():
                if key in domain_lower:
                    return float(rate)
        return 20.0  # Default fallback rate: 20 req/s

    def set_domain_rate(self, domain: str, rate: float) -> None:
        """Set or override allowed requests per second for domain."""
        with self._lock:
            self._rate_limits[domain.lower()] = float(rate)

    def acquire(self, url_or_domain: str, min_interval: Optional[float] = None) -> float:
        """Thread-safely acquire permission to execute request. Blocks if rate limit is reached.

        Returns:
            Number of seconds waited.
        """
        domain = self.extract_domain(url_or_domain)
        rate = self.get_domain_rate(domain)
        if min_interval is None:
            min_interval = 1.0 / rate if rate > 0 else 0.0

        waited = 0.0
        with self._lock:
            now = time.time()
            if domain in self._state:
                last_time, tokens = self._state[domain]
                elapsed = now - last_time
                # Refill tokens up to rate capacity
                tokens = min(rate, tokens + elapsed * rate)

                if tokens < 1.0:
                    # Need to sleep until next token is available
                    sleep_time = (1.0 - tokens) / rate if rate > 0 else 0.05
                    waited = max(0.0, sleep_time)
                    time.sleep(waited)
                    now = time.time()
                    tokens = 0.0
                else:
                    tokens -= 1.0

                self._state[domain] = (now, tokens)
            else:
                self._state[domain] = (now, max(0.0, rate - 1.0))

        return waited


_global_rate_limiter = DomainRateLimiter()


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = DEFAULT_JITTER,
) -> float:
    """Calculate exponential backoff delay with Full Jitter.

    Formula:
        backoff = min(max_delay, base_delay * (2 ** attempt))
        delay = random.uniform(base_delay * 0.5, backoff) if jitter else backoff
    """
    backoff = min(max_delay, base_delay * (2 ** attempt))
    if jitter:
        min_bound = base_delay * 0.5
        if backoff <= min_bound:
            return backoff
        return random.uniform(min_bound, backoff)
    return backoff


def parse_retry_after(response_or_header: Any) -> Optional[float]:
    """Extract and parse Retry-After header value in seconds."""
    if hasattr(response_or_header, "headers"):
        header_val = response_or_header.headers.get("Retry-After")
    elif isinstance(response_or_header, str):
        header_val = response_or_header
    else:
        header_val = None

    if not header_val:
        return None

    try:
        # Numeric seconds
        return max(0.0, float(header_val))
    except (ValueError, TypeError):
        pass

    try:
        import email.utils
        target_date = email.utils.parsedate_to_datetime(header_val)
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = (target_date - now).total_seconds()
        return max(0.0, diff)
    except Exception:
        return None


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = DEFAULT_JITTER,
    retryable_exceptions: Tuple[Type[Exception], ...] = (requests.RequestException, TimeoutError, ConnectionError),
    retryable_status_codes: Tuple[int, ...] = DEFAULT_RETRYABLE_STATUS_CODES,
    domain: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to retry a function using thread-safe exponential backoff with jitter."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            for attempt in range(max_retries + 1):
                # Rate limit pacing
                if domain:
                    _global_rate_limiter.acquire(domain)

                try:
                    res = func(*args, **kwargs)
                    # If returning a requests.Response object, check status code for retry
                    if hasattr(res, "status_code") and res.status_code in retryable_status_codes:
                        if attempt < max_retries:
                            retry_after = parse_retry_after(res)
                            sleep_time = retry_after if retry_after is not None else calculate_backoff_delay(attempt, base_delay, max_delay, jitter)
                            sys.stderr.write(
                                f"⚠️ [{func.__name__}] HTTP {res.status_code} received. "
                                f"Retrying in {sleep_time:.2f}s (attempt {attempt + 1}/{max_retries})...\n"
                            )
                            time.sleep(sleep_time)
                            continue
                    return res
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        # Check if exception has response with Retry-After
                        retry_after = None
                        if hasattr(exc, "response") and exc.response is not None:
                            retry_after = parse_retry_after(exc.response)

                        sleep_time = retry_after if retry_after is not None else calculate_backoff_delay(attempt, base_delay, max_delay, jitter)
                        sys.stderr.write(
                            f"⚠️ [{func.__name__}] {type(exc).__name__}: {exc}. "
                            f"Retrying in {sleep_time:.2f}s (attempt {attempt + 1}/{max_retries})...\n"
                        )
                        time.sleep(sleep_time)
                    else:
                        sys.stderr.write(f"❌ [{func.__name__}] Failed after {max_retries} retries: {exc}\n")
                        raise

            if last_exc:
                raise last_exc

        return wrapper  # type: ignore

    return decorator


_session_lock = threading.Lock()
_shared_session: Optional[requests.Session] = None


def get_resilient_session(pool_size: int = 50) -> requests.Session:
    """Get or initialize thread-safe requests.Session with connection pooling and retry adapters."""
    global _shared_session
    with _session_lock:
        if _shared_session is None:
            session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=pool_size,
                pool_maxsize=pool_size,
                max_retries=0,  # We handle intelligent retries at the request layer with jitter
            )
            session.mount('https://', adapter)
            session.mount('http://', adapter)
            _shared_session = session
        return _shared_session


def resilient_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = DEFAULT_JITTER,
    retryable_status_codes: Tuple[int, ...] = DEFAULT_RETRYABLE_STATUS_CODES,
    **kwargs: Any,
) -> requests.Response:
    """Execute HTTP GET with domain throttling, connection pooling, exponential backoff, and full jitter."""
    session = get_resilient_session()

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if headers:
        default_headers.update(headers)

    last_response = None
    last_exc = None

    for attempt in range(max_retries + 1):
        _global_rate_limiter.acquire(url)

        try:
            resp = session.get(url, params=params, headers=default_headers, timeout=timeout, **kwargs)
            if resp.status_code in retryable_status_codes:
                last_response = resp
                if attempt < max_retries:
                    retry_after = parse_retry_after(resp)
                    sleep_time = retry_after if retry_after is not None else calculate_backoff_delay(attempt, base_delay, max_delay, jitter)
                    sys.stderr.write(
                        f"⚠️ HTTP {resp.status_code} from {urllib.parse.urlparse(url).netloc}. "
                        f"Retrying in {sleep_time:.2f}s (attempt {attempt + 1}/{max_retries})...\n"
                    )
                    time.sleep(sleep_time)
                    continue
            return resp
        except (requests.RequestException, TimeoutError, ConnectionError) as exc:
            last_exc = exc
            if attempt < max_retries:
                sleep_time = calculate_backoff_delay(attempt, base_delay, max_delay, jitter)
                sys.stderr.write(
                    f"⚠️ Network error connecting to {urllib.parse.urlparse(url).netloc}: {exc}. "
                    f"Retrying in {sleep_time:.2f}s (attempt {attempt + 1}/{max_retries})...\n"
                )
                time.sleep(sleep_time)
            else:
                sys.stderr.write(f"❌ GET {url} failed after {max_retries} retries: {exc}\n")
                raise

    if last_response is not None:
        return last_response
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Failed to execute GET request for {url}")
