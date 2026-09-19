import os
import sys
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Union, Tuple
import requests

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass


DEFAULT_LIVE_URL = "https://api-live.exante.eu"
DEFAULT_DEMO_URL = "https://api-demo.exante.eu"


def _load_env_config() -> Dict[str, Optional[str]]:
    """Load Exante configuration from environment variables or .env file."""
    config = {
        "api_key": os.environ.get("EXANTE_API_KEY") or os.environ.get("EXANTE_APPLICATION_ID") or os.environ.get("EXANTE_CLIENT_ID"),
        "api_secret": os.environ.get("EXANTE_API_SECRET") or os.environ.get("EXANTE_SHARED_KEY") or os.environ.get("EXANTE_SECRET_KEY"),
        "account_id": os.environ.get("EXANTE_ACCOUNT_ID"),
        "api_url": os.environ.get("EXANTE_API_URL"),
        "env": (os.environ.get("EXANTE_ENV") or os.environ.get("EXANTE_ENVIRONMENT") or "live").lower(),
        "jwt_token": os.environ.get("EXANTE_JWT_TOKEN"),
    }

    if not config["api_key"] and not config["jwt_token"]:
        # Traverse up to find .env file
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            env_path = os.path.join(current, ".env")
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k in ("EXANTE_API_KEY", "EXANTE_APPLICATION_ID", "EXANTE_CLIENT_ID") and not config["api_key"]:
                                config["api_key"] = v
                            elif k in ("EXANTE_API_SECRET", "EXANTE_SHARED_KEY", "EXANTE_SECRET_KEY") and not config["api_secret"]:
                                config["api_secret"] = v
                            elif k == "EXANTE_ACCOUNT_ID" and not config["account_id"]:
                                config["account_id"] = v
                            elif k == "EXANTE_API_URL" and not config["api_url"]:
                                config["api_url"] = v
                            elif k in ("EXANTE_ENV", "EXANTE_ENVIRONMENT") and not config["env"]:
                                config["env"] = v.lower()
                            elif k == "EXANTE_JWT_TOKEN" and not config["jwt_token"]:
                                config["jwt_token"] = v
                except Exception:
                    pass
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    return config


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def generate_jwt_token(
    app_id: str,
    shared_key: str,
    client_id: Optional[str] = None,
    expires_in_seconds: int = 86400,
    scopes: Optional[List[str]] = None,
) -> str:
    """Generate an Exante OpenAPI JWT token signed with HMAC SHA-256."""
    import time
    import uuid
    import json
    import hmac
    import hashlib

    now = int(time.time())
    aud = scopes or ["symbols", "crossrates", "trade", "accounts", "summary", "feed", "change", "transactions", "historical"]
    
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": app_id,
        "aud": aud,
        "iat": now,
        "exp": now + expires_in_seconds,
        "jti": str(uuid.uuid4()),
    }
    if client_id:
        payload["sub"] = client_id

    header_b64 = _b64url_encode(json.dumps(header, separators=(',', ':')).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode("utf-8"))
    to_sign = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(shared_key.encode("utf-8"), to_sign, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


class ExanteClient:
    """Exante REST API client for accessing account summary, balances, positions and symbol info."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        api_url: Optional[str] = None,
        jwt_token: Optional[str] = None,
        env: Optional[str] = None,
        client_id: Optional[str] = None,
    ):
        env_cfg = _load_env_config()
        self.api_key = api_key or env_cfg.get("api_key")
        self.api_secret = api_secret or env_cfg.get("api_secret")
        self.account_id = account_id or env_cfg.get("account_id")
        self.jwt_token = jwt_token or env_cfg.get("jwt_token")
        self.client_id = client_id or env_cfg.get("client_id") or os.environ.get("EXANTE_USER_ID") or os.environ.get("EXANTE_CLIENT_ID")
        self.env = (env or env_cfg.get("env") or "live").lower()

        # If api_key looks like a JWT token (eyJ...)
        if self.api_key and self.api_key.startswith("eyJ") and not self.jwt_token:
            self.jwt_token = self.api_key

        if api_url:
            self.base_url = api_url.rstrip("/")
        elif env:
            self.base_url = DEFAULT_DEMO_URL if self.env == "demo" else DEFAULT_LIVE_URL
        elif env_cfg.get("api_url"):
            self.base_url = env_cfg["api_url"].rstrip("/")
        elif self.env == "demo":
            self.base_url = DEFAULT_DEMO_URL
        else:
            self.base_url = DEFAULT_LIVE_URL

        self._symbol_cache: Dict[str, Dict[str, Any]] = {}

    def is_configured(self) -> bool:
        """Check whether sufficient credentials exist to connect to Exante API."""
        return bool(self.jwt_token or (self.api_key and self.api_secret))

    def _get_auth_headers(self) -> Tuple[Optional[Tuple[str, str]], Dict[str, str]]:
        """Get HTTP auth parameters and headers."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "InvestmentSecondBrain/1.0",
        }
        auth: Optional[Tuple[str, str]] = None

        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        elif self.api_key and self.api_secret:
            auth = (self.api_key, self.api_secret)

        return auth, headers

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
        silent: bool = False,
    ) -> Any:
        """Perform an HTTP GET request to Exante API."""
        if not self.is_configured():
            raise ValueError(
                "Exante API credentials are missing. Please configure EXANTE_API_KEY and EXANTE_API_SECRET "
                "(or EXANTE_JWT_TOKEN) in your .env file or environment variables."
            )

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        auth, headers = self._get_auth_headers()

        try:
            resp = requests.get(url, auth=auth, headers=headers, params=params, timeout=timeout)
            if resp.status_code == 401:
                raise PermissionError(
                    f"Exante API authentication failed (401 Unauthorized) for URL: {url}. "
                    "Please check your EXANTE_API_KEY / EXANTE_API_SECRET credentials."
                )
            if resp.status_code == 403:
                raise PermissionError(
                    f"Exante API access forbidden (403 Forbidden) for URL: {url}. "
                    "Ensure your API key has appropriate permissions (Trade/Account read)."
                )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if not silent:
                sys.stderr.write(f"Exante API request failed for {endpoint}: {e}\n")
            raise

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Retrieve list of accounts accessible by current credentials."""
        endpoints_to_try = [
            "md/3.0/accounts",
            "trade/3.0/accounts",
        ]
        for ep in endpoints_to_try:
            try:
                res = self._request(ep)
                if isinstance(res, list):
                    return res
                elif isinstance(res, dict) and "accounts" in res:
                    return res["accounts"]
            except Exception:
                pass
        return []

    def get_account_summary(
        self,
        account_id: Optional[str] = None,
        currency: str = "EUR",
    ) -> Optional[Dict[str, Any]]:
        """Retrieve account summary (balances, positions, NAV) for the given account."""
        acc_id = account_id or self.account_id
        if not acc_id:
            accounts = self.get_accounts()
            if accounts:
                first_acc = accounts[0]
                acc_id = first_acc.get("accountId") or first_acc.get("id") or first_acc.get("account")
            if not acc_id:
                raise ValueError("No Exante account ID specified and could not discover any account from API.")

        # Try md/3.0 summary first, then trade/3.0 summary
        endpoints_to_try = [
            f"md/3.0/summary/{acc_id}/{currency}",
            f"md/3.0/summary/{acc_id}",
            f"trade/3.0/summary/{acc_id}/{currency}",
            f"trade/3.0/summary/{acc_id}",
        ]

        last_error = None
        for ep in endpoints_to_try:
            try:
                res = self._request(ep)
                if isinstance(res, dict):
                    return res
            except Exception as err:
                last_error = err

        if last_error:
            raise last_error
        return None

    def get_positions(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve active open positions for the given account."""
        acc_id = account_id or self.account_id
        endpoints = []
        if acc_id:
            endpoints.append(f"trade/3.0/positions/{acc_id}")
        endpoints.append("trade/3.0/positions")

        for ep in endpoints:
            try:
                res = self._request(ep)
                if isinstance(res, list):
                    return res
                elif isinstance(res, dict) and "positions" in res:
                    return res["positions"]
            except Exception:
                pass
        return []

    def get_symbol_info(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata (ticker, description, ISIN, currency) for a symbol."""
        if not symbol_id:
            return None
        if symbol_id in self._symbol_cache:
            return self._symbol_cache[symbol_id]

        endpoint = f"md/3.0/symbols/{symbol_id}"
        try:
            res = self._request(endpoint, silent=True)
            if isinstance(res, dict):
                self._symbol_cache[symbol_id] = res
                return res
        except Exception:
            pass

        return None

    def fetch_portfolio(
        self,
        account_id: Optional[str] = None,
        summary_currency: str = "EUR",
    ) -> Dict[str, Any]:
        """Fetch unified portfolio state (cash balances and open positions) from Exante API.

        Returns a structured dictionary matching the format expected by platforms/exante.py:
        {
            'account_id': str,
            'session_date': str (YYYY-MM-DD),
            'net_asset_value': float,
            'cash_balances': [
                {
                    'instrument': str,
                    'iso': str,
                    'value': float,
                    'currency': str
                }, ...
            ],
            'positions': [
                {
                    'ticker': str,
                    'name': str,
                    'quantity': float,
                    'avg_price': Optional[float],
                    'current_price': float,
                    'currency': str,
                    'isin': Optional[str],
                    'instrument': str,
                }, ...
            ]
        }
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            accounts = self.get_accounts()
            if accounts:
                first_acc = accounts[0]
                acc_id = first_acc.get("accountId") or first_acc.get("id") or first_acc.get("account")
            if not acc_id:
                raise ValueError("No Exante account ID specified and could not discover accounts from API.")

        summary = self.get_account_summary(acc_id, currency=summary_currency)
        if not summary:
            raise RuntimeError(f"Could not retrieve account summary for Exante account '{acc_id}'.")

        # Parse session date
        raw_session_date = summary.get("sessionDate") or summary.get("timestamp") or summary.get("date")
        if raw_session_date:
            try:
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", str(raw_session_date))
                current_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")
            except Exception:
                current_date = datetime.now().strftime("%Y-%m-%d")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")

        # 1. Parse cash balances
        currencies_raw = summary.get("currencies") or summary.get("cash") or summary.get("balances") or []
        cash_balances: List[Dict[str, Any]] = []

        if isinstance(currencies_raw, list):
            for c in currencies_raw:
                if not isinstance(c, dict):
                    continue
                code = (c.get("code") or c.get("currency") or c.get("iso") or c.get("symbol") or "").strip().upper()
                raw_val = c.get("value") if "value" in c else c.get("amount") if "amount" in c else c.get("balance")
                if not code or raw_val is None:
                    continue
                try:
                    val = float(str(raw_val).replace(",", ".").strip())
                except ValueError:
                    val = 0.0

                cash_balances.append({
                    "instrument": f"{code} Cash Balance",
                    "iso": code,
                    "value": val,
                    "currency": code,
                })
        elif isinstance(currencies_raw, dict):
            for code, raw_val in currencies_raw.items():
                code_clean = str(code).strip().upper()
                try:
                    val = float(str(raw_val).replace(",", ".").strip())
                except ValueError:
                    val = 0.0
                cash_balances.append({
                    "instrument": f"{code_clean} Cash Balance",
                    "iso": code_clean,
                    "value": val,
                    "currency": code_clean,
                })

        # 2. Parse positions
        positions_raw = summary.get("positions") or []
        if not positions_raw:
            # Fallback to direct positions endpoint if summary positions are empty
            positions_raw = self.get_positions(acc_id)

        parsed_positions: List[Dict[str, Any]] = []
        for p in positions_raw:
            if not isinstance(p, dict):
                continue
            symbol_id = (p.get("symbolId") or p.get("symbol") or p.get("instrument") or p.get("id") or "").strip()
            if not symbol_id:
                continue

            raw_qty = p.get("quantity") if "quantity" in p else p.get("qty")
            try:
                quantity = float(str(raw_qty).replace(",", ".").strip()) if raw_qty is not None else 0.0
            except ValueError:
                quantity = 0.0

            if quantity <= 0:
                continue

            raw_price = p.get("price") if "price" in p else p.get("currentPrice") if "currentPrice" in p else p.get("lastPrice")
            try:
                current_price = float(str(raw_price).replace(",", ".").strip()) if raw_price is not None else 0.0
            except ValueError:
                current_price = 0.0

            raw_avg = p.get("averagePrice") if "averagePrice" in p else p.get("avgPrice") if "avgPrice" in p else p.get("openPrice")
            try:
                avg_price = float(str(raw_avg).replace(",", ".").strip()) if raw_avg is not None else None
            except ValueError:
                avg_price = None

            currency = (p.get("currency") or "").strip().upper()
            isin = (p.get("isin") or "").strip()
            name = (p.get("name") or p.get("description") or "").strip()

            # Attempt symbol metadata enrichment if name, isin, or currency is missing
            if not isin or not name or not currency:
                sym_info = self.get_symbol_info(symbol_id)
                if sym_info:
                    if not name:
                        name = sym_info.get("name") or sym_info.get("description") or sym_info.get("ticker") or symbol_id
                    if not isin and sym_info.get("isin"):
                        isin = sym_info["isin"]
                    if not currency and sym_info.get("currency"):
                        currency = sym_info["currency"].upper()

            if not name:
                name = symbol_id
            if not currency:
                currency = "EUR"

            parsed_positions.append({
                "ticker": symbol_id,
                "instrument": symbol_id,
                "name": name,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "currency": currency,
                "isin": isin or None,
            })

        nav_raw = summary.get("netAssetValue") or summary.get("nav") or summary.get("equity")
        try:
            nav = float(str(nav_raw).replace(",", ".").strip()) if nav_raw is not None else 0.0
        except ValueError:
            nav = 0.0

        return {
            "account_id": acc_id,
            "session_date": current_date,
            "net_asset_value": nav,
            "cash_balances": cash_balances,
            "positions": parsed_positions,
        }


def get_exante_client(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    account_id: Optional[str] = None,
    api_url: Optional[str] = None,
    jwt_token: Optional[str] = None,
) -> Optional[ExanteClient]:
    """Create and return an ExanteClient instance if credentials are valid."""
    client = ExanteClient(
        api_key=api_key,
        api_secret=api_secret,
        account_id=account_id,
        api_url=api_url,
        jwt_token=jwt_token,
    )
    return client if client.is_configured() else None


def fetch_exante_portfolio(
    account_id: Optional[str] = None,
    client: Optional[ExanteClient] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch portfolio balances and positions directly from Exante API."""
    cli = client or get_exante_client(account_id=account_id)
    if not cli:
        return None
    try:
        return cli.fetch_portfolio(account_id=account_id)
    except Exception as e:
        sys.stderr.write(f"Exante API fetch failed: {e}\n")
        return None
