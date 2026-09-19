import sys
import os
import glob
import re
from typing import Optional, Dict, Any, List, Union
import requests

try:
    import yfinance as yf
except ImportError:
    yf = None

OVERVALUED_PE_THRESHOLD = 40.0
ALERT_OVERVALUED_TAG = "#alert/overvalued"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def check_overvalued(pe_ratio: Optional[Union[float, int, str]], threshold: float = OVERVALUED_PE_THRESHOLD) -> bool:
    """Check if the given PE ratio exceeds the overvalued threshold (default: 40.0)."""
    if pe_ratio is None:
        return False
    try:
        return float(pe_ratio) > threshold
    except (ValueError, TypeError):
        return False


def apply_overvalued_tag(
    tags: Optional[Union[List[str], str]],
    pe_ratio: Optional[Union[float, int, str]],
    threshold: float = OVERVALUED_PE_THRESHOLD
) -> List[str]:
    """Add or remove '#alert/overvalued' from a list of tags based on PE ratio."""
    if tags is None:
        result_tags = []
    elif isinstance(tags, (list, tuple)):
        result_tags = [str(t).strip() for t in tags if str(t).strip()]
    elif isinstance(tags, str):
        result_tags = [tags.strip()] if tags.strip() else []
    else:
        result_tags = []

    if check_overvalued(pe_ratio, threshold):
        if ALERT_OVERVALUED_TAG not in result_tags:
            result_tags.append(ALERT_OVERVALUED_TAG)
    else:
        if ALERT_OVERVALUED_TAG in result_tags:
            result_tags.remove(ALERT_OVERVALUED_TAG)

    return result_tags


def search_yahoo_symbol(query: str) -> Optional[str]:
    """Search Yahoo Finance for a ticker symbol using an ISIN or name."""
    if not query:
        return None
    url = "https://query1.finance.yahoo.com/v1/finance/search"
    try:
        resp = requests.get(url, params={"q": query, "quotesCount": 1}, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            if quotes:
                return quotes[0].get("symbol")
    except Exception:
        pass
    return None


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Calculate the Relative Strength Index (RSI) using Wilder's smoothing method."""
    if not prices or len(prices) <= period:
        return None
    try:
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]

        # Initial simple average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Wilder's smoothing
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi, 2)
    except Exception:
        return None


def fetch_yfinance_data(isin: Optional[str], name: str, ticker: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch metadata from Yahoo Finance via the yfinance library or a HTTP fallback."""
    symbol = search_yahoo_symbol(isin) if isin else None
    if not symbol and ticker:
        base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
        symbol = search_yahoo_symbol(ticker) or search_yahoo_symbol(base_ticker)
    if not symbol:
        symbol = search_yahoo_symbol(name)
    if not symbol:
        return None

    data: Dict[str, Any] = {"yahoo_ticker": symbol}

    if yf is not None:
        try:
            ticker_obj = yf.Ticker(symbol)
            info = ticker_obj.info or {}
            if info:
                if info.get("sector"):
                    data["sector"] = info["sector"]
                if info.get("industry"):
                    data["industry"] = info["industry"]
                if info.get("country"):
                    data["country"] = info["country"]
                mcap = info.get("marketCap")
                if mcap:
                    if mcap >= 1e12:
                        data["market_cap"] = f"{mcap / 1e12:.2f}T"
                    elif mcap >= 1e9:
                        data["market_cap"] = f"{mcap / 1e9:.2f}B"
                    elif mcap >= 1e6:
                        data["market_cap"] = f"{mcap / 1e6:.2f}M"
                    else:
                        data["market_cap"] = str(mcap)
                pe = info.get("trailingPE") or info.get("forwardPE")
                if pe:
                    pe_val = round(pe, 2)
                    data["pe_ratio"] = pe_val
                    if pe_val > OVERVALUED_PE_THRESHOLD:
                        tags = data.setdefault("tags", [])
                        if ALERT_OVERVALUED_TAG not in tags:
                            tags.append(ALERT_OVERVALUED_TAG)

                div_val = None
                dy = info.get("dividendYield")
                yd = info.get("yield")
                tady = info.get("trailingAnnualDividendYield")
                if dy is not None and dy > 0:
                    div_val = dy
                elif yd is not None and yd > 0:
                    div_val = yd * 100
                elif tady is not None and tady > 0:
                    div_val = tady * 100
                if div_val is not None and div_val > 0:
                    data["dividend_yield"] = f"{div_val:.2f}%"

                ms_rating = (
                    info.get("morningStarOverallRating")
                    or info.get("morningstarOverallRating")
                    or info.get("morningStarRating")
                    or info.get("morningstarRating")
                )
                if ms_rating is not None:
                    data["morningstar_rating"] = ms_rating

                ms_risk = (
                    info.get("morningStarRiskRating")
                    or info.get("morningstarRiskRating")
                    or info.get("morningStarRisk")
                    or info.get("morningstarRisk")
                )
                if ms_risk is not None:
                    data["morningstar_risk"] = ms_risk

                # Forward P/E
                fwd_pe = info.get("forwardPE")
                if fwd_pe is not None:
                    try:
                        data["forward_pe"] = round(float(fwd_pe), 2)
                    except (ValueError, TypeError):
                        pass

                # Beta
                beta = info.get("beta")
                if beta is not None:
                    try:
                        data["beta"] = round(float(beta), 2)
                    except (ValueError, TypeError):
                        pass

                # 52-week High / Low
                high_52 = info.get("fiftyTwoWeekHigh")
                if high_52 is not None:
                    try:
                        data["fifty_two_week_high"] = round(float(high_52), 2)
                    except (ValueError, TypeError):
                        pass

                low_52 = info.get("fiftyTwoWeekLow")
                if low_52 is not None:
                    try:
                        data["fifty_two_week_low"] = round(float(low_52), 2)
                    except (ValueError, TypeError):
                        pass

                # 52-week Drawdown
                curr_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                if curr_price is not None and high_52 is not None:
                    try:
                        cp = float(curr_price)
                        hp = float(high_52)
                        if hp > 0:
                            dd = ((cp - hp) / hp) * 100.0
                            data["drawdown_52w"] = f"{dd:.2f}%"
                    except (ValueError, TypeError):
                        pass

                # Moving Averages (SMA 50, SMA 200)
                sma_50 = info.get("fiftyDayAverage")
                if sma_50 is not None:
                    try:
                        data["sma_50"] = round(float(sma_50), 2)
                    except (ValueError, TypeError):
                        pass

                sma_200 = info.get("twoHundredDayAverage")
                if sma_200 is not None:
                    try:
                        data["sma_200"] = round(float(sma_200), 2)
                    except (ValueError, TypeError):
                        pass

                # RSI (14-day)
                try:
                    hist = ticker_obj.history(period="2mo")
                    if hist is not None and not hist.empty and "Close" in hist:
                        closes = [float(c) for c in hist["Close"].dropna().tolist()]
                        rsi = calculate_rsi(closes, period=14)
                        if rsi is not None:
                            data["rsi_14"] = rsi
                except Exception:
                    pass

                return data
        except Exception as e:
            sys.stderr.write(f"yfinance failed for {symbol}: {e}\n")

    # Fallback via Yahoo Finance public API
    try:
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {"modules": "summaryProfile,financialData,defaultKeyStatistics,summaryDetail,fundProfile,fundPerformance"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            raw = resp.json()
            result = raw.get("quoteSummary", {}).get("result", [{}])[0]
            profile = result.get("summaryProfile", {})
            financials = result.get("financialData", {})
            stats = result.get("defaultKeyStatistics", {})
            summary_detail = result.get("summaryDetail", {})
            fund_profile = result.get("fundProfile", {})
            fund_perf = result.get("fundPerformance", {})
            if profile.get("sector"):
                data["sector"] = profile["sector"]
            if profile.get("industry"):
                data["industry"] = profile["industry"]
            if profile.get("country"):
                data["country"] = profile["country"]

            def get_val(obj):
                return obj.get("raw") if isinstance(obj, dict) else obj

            mcap = get_val(financials.get("marketCap") or stats.get("marketCap"))
            if mcap:
                if mcap >= 1e12:
                    data["market_cap"] = f"{mcap / 1e12:.2f}T"
                elif mcap >= 1e9:
                    data["market_cap"] = f"{mcap / 1e9:.2f}B"
                elif mcap >= 1e6:
                    data["market_cap"] = f"{mcap / 1e6:.2f}M"
                else:
                    data["market_cap"] = str(mcap)
            pe = (get_val(financials.get("trailingPE")) or get_val(stats.get("trailingPE")) or get_val(stats.get("forwardPE")))
            if pe:
                pe_val = round(pe, 2)
                data["pe_ratio"] = pe_val
                if pe_val > OVERVALUED_PE_THRESHOLD:
                    tags = data.setdefault("tags", [])
                    if ALERT_OVERVALUED_TAG not in tags:
                        tags.append(ALERT_OVERVALUED_TAG)
            div = (get_val(financials.get("dividendYield")) or
                   get_val(stats.get("dividendYield")) or
                   get_val(financials.get("yield")) or
                   get_val(stats.get("yield")) or
                   get_val(stats.get("trailingAnnualDividendYield")))
            if div is not None and div > 0:
                val = div * 100 if div < 1 else div
                data["dividend_yield"] = f"{val:.2f}%"

            ms_rating = (
                get_val(fund_perf.get("morningStarOverallRating"))
                or get_val(fund_profile.get("morningStarOverallRating"))
                or get_val(stats.get("morningStarOverallRating"))
                or get_val(fund_perf.get("morningstarOverallRating"))
                or get_val(fund_profile.get("morningstarOverallRating"))
                or get_val(stats.get("morningstarOverallRating"))
            )
            if ms_rating is not None:
                data["morningstar_rating"] = ms_rating

            ms_risk = (
                get_val(fund_perf.get("morningStarRiskRating"))
                or get_val(fund_profile.get("morningStarRiskRating"))
                or get_val(stats.get("morningStarRiskRating"))
                or get_val(fund_perf.get("morningstarRiskRating"))
                or get_val(fund_profile.get("morningstarRiskRating"))
                or get_val(stats.get("morningstarRiskRating"))
            )
            if ms_risk is not None:
                data["morningstar_risk"] = ms_risk

            fwd_pe = get_val(summary_detail.get("forwardPE") or stats.get("forwardPE"))
            if fwd_pe is not None:
                try:
                    data["forward_pe"] = round(float(fwd_pe), 2)
                except (ValueError, TypeError):
                    pass

            beta = get_val(summary_detail.get("beta") or stats.get("beta"))
            if beta is not None:
                try:
                    data["beta"] = round(float(beta), 2)
                except (ValueError, TypeError):
                    pass

            high_52 = get_val(summary_detail.get("fiftyTwoWeekHigh"))
            if high_52 is not None:
                try:
                    data["fifty_two_week_high"] = round(float(high_52), 2)
                except (ValueError, TypeError):
                    pass

            low_52 = get_val(summary_detail.get("fiftyTwoWeekLow"))
            if low_52 is not None:
                try:
                    data["fifty_two_week_low"] = round(float(low_52), 2)
                except (ValueError, TypeError):
                    pass

            sma_50 = get_val(summary_detail.get("fiftyDayAverage"))
            if sma_50 is not None:
                try:
                    data["sma_50"] = round(float(sma_50), 2)
                except (ValueError, TypeError):
                    pass

            sma_200 = get_val(summary_detail.get("twoHundredDayAverage"))
            if sma_200 is not None:
                try:
                    data["sma_200"] = round(float(sma_200), 2)
                except (ValueError, TypeError):
                    pass

            curr_price = get_val(financials.get("currentPrice") or summary_detail.get("previousClose"))
            if curr_price is not None and high_52 is not None:
                try:
                    cp = float(curr_price)
                    hp = float(high_52)
                    if hp > 0:
                        dd = ((cp - hp) / hp) * 100.0
                        data["drawdown_52w"] = f"{dd:.2f}%"
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    return data if len(data) > 1 else None


def fetch_yfinance_analyst_rating(symbol: str) -> Optional[str]:
    """Fetch analyst recommendation consensus from Yahoo Finance for a ticker symbol."""
    if not symbol:
        return None

    mapping = {
        "strong_buy": "Strong Buy",
        "buy": "Buy",
        "hold": "Hold",
        "underperform": "Sell",
        "sell": "Sell",
        "strong_sell": "Strong Sell"
    }

    if yf is not None:
        try:
            ticker_obj = yf.Ticker(symbol)
            info = ticker_obj.info or {}
            rec = info.get("recommendationKey")
            if rec and str(rec).lower() not in ("none", "null", ""):
                rec_clean = str(rec).lower().strip()
                return mapping.get(rec_clean, rec_clean.replace("_", " ").title())
        except Exception as e:
            sys.stderr.write(f"yfinance recommendation fetch failed for {symbol}: {e}\n")

    try:
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {"modules": "financialData"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            raw = resp.json()
            result = raw.get("quoteSummary", {}).get("result", [{}])[0]
            financials = result.get("financialData", {})
            rec = financials.get("recommendationKey")
            if rec and str(rec).lower() not in ("none", "null", ""):
                rec_clean = str(rec).lower().strip()
                return mapping.get(rec_clean, rec_clean.replace("_", " ").title())
    except Exception:
        pass

    return None


_fx_cache: Dict[str, float] = {'PLN': 1.0}


def get_fx_rate_to_pln(currency: str) -> float:
    """Fetch FX exchange rate from specified currency to PLN via yfinance or Yahoo Finance API."""
    if not currency:
        return 1.0
    curr = str(currency).strip().upper()
    if curr == 'PLN':
        return 1.0
    if curr in _fx_cache:
        return _fx_cache[curr]

    symbol = f"{curr}PLN=X"
    if yf is not None:
        try:
            ticker_obj = yf.Ticker(symbol)
            price = None
            if hasattr(ticker_obj, 'fast_info') and ticker_obj.fast_info:
                price = ticker_obj.fast_info.get('last_price')
            if not price and ticker_obj.info:
                price = ticker_obj.info.get('regularMarketPrice') or ticker_obj.info.get('previousClose')
            if not price:
                hist = ticker_obj.history(period="1d")
                if not hist.empty and 'Close' in hist:
                    price = float(hist['Close'].iloc[-1])
            if price and float(price) > 0:
                rate = float(price)
                _fx_cache[curr] = rate
                return rate
        except Exception as e:
            sys.stderr.write(f"yfinance FX rate fetch failed for {symbol}: {e}\n")

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        resp = requests.get(url, params={"interval": "1d", "range": "1d"}, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            raw = resp.json()
            meta = raw.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
            if price and float(price) > 0:
                rate = float(price)
                _fx_cache[curr] = rate
                return rate
    except Exception:
        pass

    return 1.0


def calculate_value_pln(quantity: Optional[float], current_price: Optional[float], currency: str) -> Optional[float]:
    """Calculate asset value in PLN based on quantity, current_price, and currency FX rate."""
    if quantity is None or current_price is None:
        return None
    try:
        q = float(quantity)
        p = float(current_price)
        rate = get_fx_rate_to_pln(currency)
        res = q * p * rate
        return int(res) if res.is_integer() else round(res, 2)
    except (ValueError, TypeError):
        return None


def fetch_yfinance_top_holdings(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch top holdings list for an ETF from Yahoo Finance funds_data."""
    if not symbol:
        return []
    holdings: List[Dict[str, Any]] = []

    if yf is not None:
        try:
            ticker_obj = yf.Ticker(symbol)
            if hasattr(ticker_obj, 'funds_data') and ticker_obj.funds_data is not None:
                th = getattr(ticker_obj.funds_data, 'top_holdings', None)
                if th is not None and not th.empty:
                    for idx, row in th.head(limit).iterrows():
                        pct = row.get('Holding Percent', 0.0)
                        if pct is not None:
                            try:
                                pct_val = round(float(pct) * 100, 2)
                            except (ValueError, TypeError):
                                pct_val = 0.0
                        else:
                            pct_val = 0.0
                        holdings.append({
                            "ticker": str(idx).strip(),
                            "name": str(row.get('Name', '')).strip(),
                            "weight_pct": pct_val
                        })
        except Exception as e:
            sys.stderr.write(f"yfinance funds_data fetch failed for {symbol}: {e}\n")

    return holdings[:limit]


def normalize_international_ticker(symbol: str, name: Optional[str] = None) -> str:
    """Normalize international exchange ticker symbols for Yahoo Finance."""
    sym = symbol.strip() if symbol else ""
    if not sym:
        return ""

    # HKEX 5-digit numeric codes: e.g. 00939 -> 0939.HK, 01398 -> 1398.HK, 03988 -> 3988.HK
    if sym.isdigit() and len(sym) == 5:
        return f"{int(sym):04d}.HK"

    # KRX 6-digit numeric codes: e.g. 012450 -> 012450.KS
    if sym.isdigit() and len(sym) == 6:
        return f"{sym}.KS"

    # Brazilian B3 codes: e.g. PETR4 -> PETR4.SA, ITSA4 -> ITSA4.SA, VALE3 -> VALE3.SA
    if re.match(r'^[A-Z]{4}\d$', sym):
        return f"{sym}.SA"

    return sym


def fetch_company_fundamentals(symbol_or_name: str, fallback_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch fundamental details for a single company/holding using Yahoo Finance."""
    if not symbol_or_name:
        return {}

    raw_symbol = symbol_or_name.strip()
    candidate_name = (fallback_name or symbol_or_name).strip()

    symbol = normalize_international_ticker(raw_symbol, candidate_name)

    # If the string contains spaces or looks like a full name, search for its symbol
    if " " in symbol or len(symbol) > 12:
        found_symbol = search_yahoo_symbol(symbol)
        if found_symbol:
            symbol = found_symbol

    data: Dict[str, Any] = {
        "ticker": raw_symbol,
        "yahoo_ticker": symbol,
        "name": candidate_name if candidate_name != raw_symbol else raw_symbol,
        "sector": None,
        "industry": None,
        "country": None,
        "market_cap": None,
        "pe_ratio": None,
        "dividend_yield": None,
        "current_price": None,
        "currency": "USD"
    }

    if yf is not None:
        info = {}
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
        except Exception:
            info = {}

        if not info or not info.get("shortName"):
            # Try searching by fallback name if initial symbol failed
            query_name = fallback_name or symbol_or_name
            if query_name:
                fallback_sym = search_yahoo_symbol(query_name)
                if fallback_sym and fallback_sym != symbol:
                    try:
                        symbol = fallback_sym
                        data["yahoo_ticker"] = symbol
                        t = yf.Ticker(symbol)
                        info = t.info or {}
                    except Exception:
                        info = {}

        if info:
            comp_name = info.get("longName") or info.get("shortName")
            if comp_name:
                data["name"] = comp_name
            data["sector"] = info.get("sector")
            data["industry"] = info.get("industry")
            data["country"] = info.get("country")
            data["currency"] = info.get("currency", "USD")

            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if price is not None:
                try:
                    data["current_price"] = round(float(price), 2)
                except (ValueError, TypeError):
                    pass

            mcap = info.get("marketCap")
            if mcap:
                if mcap >= 1e12:
                    data["market_cap"] = f"{mcap / 1e12:.2f}T"
                elif mcap >= 1e9:
                    data["market_cap"] = f"{mcap / 1e9:.2f}B"
                elif mcap >= 1e6:
                    data["market_cap"] = f"{mcap / 1e6:.2f}M"
                else:
                    data["market_cap"] = str(mcap)

            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe:
                try:
                    data["pe_ratio"] = round(float(pe), 2)
                except (ValueError, TypeError):
                    pass

            dy = info.get("dividendYield") or info.get("yield") or info.get("trailingAnnualDividendYield")
            if dy is not None and dy > 0:
                val = dy * 100 if dy < 1 else dy
                data["dividend_yield"] = f"{val:.2f}%"

            return data

    return data


def update_overvalued_alerts(assets_dir: Optional[str] = None) -> int:
    """Scan all asset files in 10_Finance/Assets and update #alert/overvalued tags based on pe_ratio."""
    if assets_dir is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.abspath(os.path.join(current_dir, "../../../../10_Finance/Assets"))

    if not os.path.exists(assets_dir):
        sys.stderr.write(f"Assets directory not found: {assets_dir}\n")
        return 0

    scripts_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if scripts_dir not in sys.path:
        sys.path.append(scripts_dir)

    try:
        from model.asset import Asset
    except ImportError:
        Asset = None

    md_files = glob.glob(os.path.join(assets_dir, "*.md"))
    updated_count = 0

    for file_path in md_files:
        if Asset:
            asset = Asset.from_file(file_path)
            new_tags = apply_overvalued_tag(asset.tags, asset.pe_ratio)
            if new_tags != asset.tags:
                asset.tags = new_tags
                asset.save(file_path)
                updated_count += 1
                print(f"Updated alerts for {os.path.basename(file_path)}: tags={asset.tags}")

    return updated_count
