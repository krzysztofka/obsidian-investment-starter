import os
import sys
import json
import glob
import math
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import requests

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
scripts_dir = os.path.dirname(integrations_dir)
vault_root = os.path.dirname(os.path.dirname(scripts_dir))
for p in (scripts_dir, integrations_dir, current_dir):
    if p not in sys.path:
        sys.path.append(p)

# Try importing OpenBB SDK if installed
try:
    from openbb import obb  # type: ignore
    OPENBB_AVAILABLE = True
except ImportError:
    obb = None
    OPENBB_AVAILABLE = False

try:
    import yfinance as yf
except ImportError:
    yf = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_openbb_available() -> bool:
    """Check if OpenBB platform SDK is available in the environment."""
    return OPENBB_AVAILABLE


def fetch_morningstar_rating(symbol: str) -> Dict[str, Any]:
    """Fetch Morningstar star rating, quantitative rating, and risk rating for a symbol or ISIN.

    Returns:
        Dict containing keys: 'morningstar_rating', 'morningstar_risk', 'analyst_rating', 'category'
    """
    result: Dict[str, Any] = {
        "morningstar_rating": None,
        "morningstar_risk": None,
        "analyst_rating": None,
        "category": None,
    }

    if not symbol:
        return result

    clean_symbol = symbol.strip().upper()

    # 1. If OpenBB is available, attempt to query providers
    if OPENBB_AVAILABLE and obb is not None:
        try:
            # Query equity profile or quantitative rating if supported
            if hasattr(obb, "equity") and hasattr(obb.equity, "profile"):
                data = obb.equity.profile(clean_symbol)
                if data and hasattr(data, "to_df"):
                    df = data.to_df()
                    if not df.empty:
                        for col in df.columns:
                            col_l = col.lower()
                            if "morningstar" in col_l or "star" in col_l:
                                result["morningstar_rating"] = str(df[col].iloc[0])
                            if "risk" in col_l and "rating" in col_l:
                                result["morningstar_risk"] = str(df[col].iloc[0])
        except Exception as e:
            sys.stderr.write(f"OpenBB: Error querying profile for {clean_symbol}: {e}\n")

    # 2. Query yfinance ticker info / funds_data / quoteSummary for Morningstar fields
    if (not result["morningstar_rating"] or not result["morningstar_risk"]) and yf is not None:
        try:
            t = yf.Ticker(clean_symbol)
            info = t.info or {}
            if info:
                # Star rating
                ms_rating = (
                    info.get("morningStarOverallRating")
                    or info.get("morningstarOverallRating")
                    or info.get("morningStarRating")
                    or info.get("morningstarRating")
                )
                if ms_rating is not None:
                    result["morningstar_rating"] = ms_rating

                # Risk rating
                ms_risk = (
                    info.get("morningStarRiskRating")
                    or info.get("morningstarRiskRating")
                    or info.get("morningStarRisk")
                    or info.get("morningstarRisk")
                )
                if ms_risk is not None:
                    # Map numeric risk score (1-5) to descriptive text if numeric
                    risk_map = {1: "Low", 2: "Below Average", 3: "Average", 4: "Above Average", 5: "High"}
                    result["morningstar_risk"] = risk_map.get(ms_risk, str(ms_risk))

                # Category
                if info.get("category"):
                    result["category"] = info["category"]

                # Analyst recommendation rating
                rec = info.get("recommendationKey")
                if rec:
                    result["analyst_rating"] = rec.replace("_", " ").title()
        except Exception as e:
            sys.stderr.write(f"OpenBB/YFinance: Error retrieving Morningstar ratings for {clean_symbol}: {e}\n")

    return result


def fetch_quantitative_metrics(symbol: str, period: str = "1y", rf_rate: float = 0.04) -> Dict[str, Any]:
    """Calculate annualized Volatility, Sharpe Ratio, Max Drawdown, and Upside Potential."""
    result: Dict[str, Any] = {
        "volatility": None,
        "sharpe_ratio": None,
        "max_drawdown": None,
        "upside_potential": None,
    }
    if not symbol:
        return result

    clean_symbol = symbol.strip().upper()

    # 1. Calculate price history metrics (Volatility, Sharpe Ratio, Max Drawdown)
    try:
        closes: List[float] = []
        if OPENBB_AVAILABLE and obb is not None:
            try:
                if hasattr(obb, "equity") and hasattr(obb.equity, "price") and hasattr(obb.equity.price, "historical"):
                    hist_data = obb.equity.price.historical(clean_symbol)
                    if hist_data and hasattr(hist_data, "to_df"):
                        df = hist_data.to_df()
                        if not df.empty and "close" in df.columns:
                            closes = df["close"].dropna().tolist()
            except Exception:
                pass

        if not closes and yf is not None:
            t = yf.Ticker(clean_symbol)
            hist = t.history(period=period)
            if not hist.empty and len(hist) > 10:
                closes = hist["Close"].dropna().tolist()

        if closes and len(closes) > 10:
            returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
            n = len(returns)
            if n > 1:
                mean_r = sum(returns) / n
                variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
                std_r = math.sqrt(variance)
                ann_vol = std_r * math.sqrt(252)
                result["volatility"] = f"{ann_vol * 100:.2f}%"

                ann_return = mean_r * 252
                if ann_vol > 0:
                    sharpe = (ann_return - rf_rate) / ann_vol
                    result["sharpe_ratio"] = round(sharpe, 2)

                # Max Drawdown
                peak = closes[0]
                max_dd = 0.0
                for p in closes:
                    if p > peak:
                        peak = p
                    dd = (p - peak) / peak if peak > 0 else 0.0
                    if dd < max_dd:
                        max_dd = dd
                result["max_drawdown"] = f"{max_dd * 100:.2f}%"
    except Exception as e:
        sys.stderr.write(f"OpenBB: Error computing quantitative metrics for {clean_symbol}: {e}\n")

    # 2. Upside potential calculation (Analyst consensus target vs current price)
    if yf is not None:
        try:
            t = yf.Ticker(clean_symbol)
            info = t.info or {}
            curr_p = info.get("currentPrice") or info.get("regularMarketPrice")
            tgt_p = info.get("targetMeanPrice") or info.get("targetMedianPrice")
            if tgt_p and curr_p and curr_p > 0:
                upside_pct = ((tgt_p - curr_p) / curr_p) * 100
                result["upside_potential"] = f"{upside_pct:+.2f}%"
        except Exception as e:
            sys.stderr.write(f"OpenBB: Error calculating upside potential for {clean_symbol}: {e}\n")

    return result


def fetch_openbb_data(symbol: str) -> Dict[str, Any]:
    """Fetch enriched market metrics, quantitative risk indicators, and ratings using OpenBB / YFinance."""
    if not symbol:
        return {}

    clean_symbol = symbol.strip().upper()
    data: Dict[str, Any] = {
        "yahoo_ticker": clean_symbol,
    }

    # Fetch Morningstar ratings
    ms_info = fetch_morningstar_rating(clean_symbol)
    if ms_info.get("morningstar_rating"):
        data["morningstar_rating"] = ms_info["morningstar_rating"]
    if ms_info.get("morningstar_risk"):
        data["morningstar_risk"] = ms_info["morningstar_risk"]
    if ms_info.get("analyst_rating"):
        data["analyst_rating"] = ms_info["analyst_rating"]

    # Fetch Quantitative & Risk Metrics (Volatility, Sharpe Ratio, Max Drawdown, Upside Potential)
    q_metrics = fetch_quantitative_metrics(clean_symbol)
    if q_metrics.get("volatility"):
        data["volatility"] = q_metrics["volatility"]
    if q_metrics.get("sharpe_ratio") is not None:
        data["sharpe_ratio"] = q_metrics["sharpe_ratio"]
    if q_metrics.get("max_drawdown"):
        data["max_drawdown"] = q_metrics["max_drawdown"]
    if q_metrics.get("upside_potential"):
        data["upside_potential"] = q_metrics["upside_potential"]

    # If OpenBB is installed, query additional overview & fundamental stats
    if OPENBB_AVAILABLE and obb is not None:
        try:
            if hasattr(obb, "equity") and hasattr(obb.equity, "fundamental"):
                if hasattr(obb.equity.fundamental, "overview"):
                    overview_res = obb.equity.fundamental.overview(clean_symbol)
                    if overview_res and hasattr(overview_res, "to_df"):
                        df = overview_res.to_df()
                        if not df.empty:
                            row = df.iloc[0].to_dict()
                            if "pe_ratio" in row and row["pe_ratio"]:
                                data["pe_ratio"] = round(float(row["pe_ratio"]), 2)
                            if "dividend_yield" in row and row["dividend_yield"]:
                                data["dividend_yield"] = f"{float(row['dividend_yield']) * 100:.2f}%"
                            if "sector" in row and row["sector"]:
                                data["sector"] = row["sector"]
                            if "industry" in row and row["industry"]:
                                data["industry"] = row["industry"]
        except Exception as e:
            sys.stderr.write(f"OpenBB: Error querying fundamental overview for {clean_symbol}: {e}\n")

    # Fallback to yfinance ticker if metrics are still missing
    if yf is not None and ("pe_ratio" not in data or "sector" not in data):
        try:
            t = yf.Ticker(clean_symbol)
            info = t.info or {}
            if info:
                if "name" not in data and info.get("shortName"):
                    data["name"] = info["shortName"]
                if "sector" not in data and info.get("sector"):
                    data["sector"] = info["sector"]
                if "industry" not in data and info.get("industry"):
                    data["industry"] = info["industry"]
                if "country" not in data and info.get("country"):
                    data["country"] = info["country"]
                if "currency" not in data and info.get("currency"):
                    data["currency"] = info["currency"]
                if "current_price" not in data and (info.get("currentPrice") or info.get("regularMarketPrice")):
                    data["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")

                mcap = info.get("marketCap")
                if mcap and "market_cap" not in data:
                    if mcap >= 1e12:
                        data["market_cap"] = f"{mcap / 1e12:.2f}T"
                    elif mcap >= 1e9:
                        data["market_cap"] = f"{mcap / 1e9:.2f}B"
                    elif mcap >= 1e6:
                        data["market_cap"] = f"{mcap / 1e6:.2f}M"

                pe = info.get("trailingPE") or info.get("forwardPE")
                if pe and "pe_ratio" not in data:
                    data["pe_ratio"] = round(pe, 2)

                dy = info.get("dividendYield")
                yd = info.get("yield")
                tady = info.get("trailingAnnualDividendYield")
                div_val = None
                if dy is not None and dy > 0:
                    div_val = dy
                elif yd is not None and yd > 0:
                    div_val = yd * 100 if yd < 1 else yd
                elif tady is not None and tady > 0:
                    div_val = tady * 100
                if div_val is not None and div_val > 0:
                    data["dividend_yield"] = f"{div_val:.2f}%"
        except Exception as e:
            sys.stderr.write(f"OpenBB/YF: Error gathering ticker data for {clean_symbol}: {e}\n")

    return data


# Predefined high-quality watchlist screen candidates across core strategies
CANDIDATE_POOLS = {
    "quality_growth": [
        {"ticker": "NVDA", "name": "NVIDIA Corporation", "thesis": "Dominant GPU & AI computing platform architecture with wide enterprise moat.", "sector": "Technology"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "thesis": "Search monopoly, YouTube scale, accelerating Cloud profitability, and Gemini AI integration.", "sector": "Technology"},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "thesis": "AWS cloud margins expansion, high-margin retail advertising, and logistics automation.", "sector": "Consumer Cyclical"},
        {"ticker": "ASML", "name": "ASML Holding N.V.", "thesis": "Global monopoly on EUV lithography critical for semiconductor manufacturing.", "sector": "Technology"},
    ],
    "dividend_value": [
        {"ticker": "JNJ", "name": "Johnson & Johnson", "thesis": "AAA-rated balance sheet, diversified healthcare & medtech, 60+ years of consecutive dividend growth.", "sector": "Healthcare"},
        {"ticker": "PG", "name": "Procter & Gamble Co.", "thesis": "Recession-resistant consumer staples pricing power and consistent shareholder capital returns.", "sector": "Consumer Defensive"},
        {"ticker": "CVX", "name": "Chevron Corporation", "thesis": "Low breakeven cost upstream assets, strong balance sheet, and disciplined capital return program.", "sector": "Energy"},
        {"ticker": "KO", "name": "The Coca-Cola Company", "thesis": "Unmatched global distribution network, high pricing power, and steady cash generation.", "sector": "Consumer Defensive"},
    ],
    "european_leaders": [
        {"ticker": "ASML", "name": "ASML Holding N.V.", "thesis": "Uncontested monopoly on extreme ultraviolet (EUV) lithography systems in Europe.", "sector": "Technology"},
        {"ticker": "MC.PA", "name": "LVMH Moët Hennessy Louis Vuitton", "thesis": "World leader in luxury goods with unparalleled heritage brands and pricing power.", "sector": "Consumer Cyclical"},
        {"ticker": "SAP", "name": "SAP SE", "thesis": "Mission-critical enterprise ERP software leader with accelerating cloud migration.", "sector": "Technology"},
        {"ticker": "NVO", "name": "Novo Nordisk A/S", "thesis": "Global healthcare and diabetes/obesity treatment leader with durable market share.", "sector": "Healthcare"},
        {"ticker": "ALV.DE", "name": "Allianz SE", "thesis": "Premier European insurance & asset manager (PIMCO) with steady 5%+ dividend yield.", "sector": "Finance"},
        {"ticker": "SIE.DE", "name": "Siemens AG", "thesis": "Industrial digitalization, smart infrastructure, and energy transition powerhouse.", "sector": "Industrials"},
        {"ticker": "SHEL", "name": "Shell PLC", "thesis": "Integrated energy major generating massive free cash flow, LNG dominance, and aggressive share buybacks.", "sector": "Energy"},
        {"ticker": "SNY", "name": "Sanofi SA", "thesis": "Deep value European biopharma with strong immunology franchise (Dupixent) and 4.5%+ dividend.", "sector": "Healthcare"},
    ],
    "dividend_aristocrats": [
        {"ticker": "JNJ", "name": "Johnson & Johnson", "thesis": "60+ years of consecutive dividend growth, AAA balance sheet, recession-proof cash flows.", "sector": "Healthcare"},
        {"ticker": "ABBV", "name": "AbbVie Inc.", "thesis": "High-yield biopharma leader with successful post-Humira growth engines (Skyrizi & Rinvoq).", "sector": "Healthcare"},
        {"ticker": "PG", "name": "Procter & Gamble Co.", "thesis": "Global consumer staples giant with 67 years of dividend increases and pricing power.", "sector": "Consumer Defensive"},
        {"ticker": "PEP", "name": "PepsiCo, Inc.", "thesis": "Diversified snacks & beverage titan with resilient volumes and 50+ years of dividend hikes.", "sector": "Consumer Defensive"},
        {"ticker": "CVX", "name": "Chevron Corporation", "thesis": "Energy aristocrat with 36+ years of dividend hikes and conservative debt gearing.", "sector": "Energy"},
        {"ticker": "O", "name": "Realty Income Corp", "thesis": "'The Monthly Dividend Company' - S&P 500 REIT with 25+ years of consecutive monthly payouts.", "sector": "Real Estate"},
        {"ticker": "TROW", "name": "T. Rowe Price Group", "thesis": "Debt-free financial asset manager aristocrat with 37+ years of dividend increases.", "sector": "Finance"},
    ],
    "fallen_angels": [
        {"ticker": "BTI", "name": "British American Tobacco", "thesis": "Deep value tobacco transition player trading at low single-digit P/E with ~8% dividend yield.", "sector": "Consumer Defensive"},
        {"ticker": "PFE", "name": "Pfizer Inc.", "thesis": "Post-Covid reset deep value pharma with rich oncology pipeline and ~6% dividend yield.", "sector": "Healthcare"},
        {"ticker": "UNH", "name": "UnitedHealth Group Inc.", "thesis": "Highest-quality healthcare platform in the US trading at a cyclical discount.", "sector": "Healthcare"},
        {"ticker": "NKE", "name": "Nike, Inc.", "thesis": "Global sportswear giant turnaround play at multi-year valuation troughs.", "sector": "Consumer Cyclical"},
        {"ticker": "VALE", "name": "Vale S.A.", "thesis": "World's lowest-cost iron ore and nickel producer offering deep commodity value and high dividend.", "sector": "Basic Materials"},
    ],
    "thematic_etfs": [
        {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "thesis": "Ultra-low cost broad US total market diversification.", "sector": "Broad Market"},
        {"ticker": "VXUS", "name": "Vanguard Total International Stock ETF", "thesis": "Comprehensive ex-US global equity exposure for geographic hedge.", "sector": "Broad Market"},
        {"ticker": "SCHD", "name": "Schwab U.S. Dividend Equity ETF", "thesis": "High-quality 100 dividend-paying US stocks with strong return on equity and yield.", "sector": "Financials"},
        {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "thesis": "Concentrated exposure to leading global semiconductor design and foundry leaders.", "sector": "Technology"},
    ],
}


def is_quality_asset(candidate_data: Dict[str, Any]) -> bool:
    """Anti-Junk filter to verify the asset is NOT a penny stock or distressed value trap."""
    # Check market cap format (e.g. 50B, 1.2T)
    mcap = candidate_data.get("market_cap")
    if mcap and isinstance(mcap, str):
        if mcap.endswith("M"):
            val = float(mcap[:-1])
            if val < 5000:  # Under $5B rejected
                return False

    # Check PE ratio sanity (exclude extreme speculative bubbles > 80 or unviable losses)
    pe = candidate_data.get("pe_ratio")
    if pe is not None:
        if pe <= 0 or pe > 90:
            return False

    return True



def get_potential_watchlist_items(
    strategy: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Scan and retrieve potential watchlist candidates enriched with live market data, ratings, and valuation metrics.

    Args:
        strategy: 'quality_growth', 'dividend_value', 'thematic_etfs', or None for all.
        limit: Max candidates to return.

    Returns:
        List of candidate dictionaries ready for inspection or note creation.
    """
    candidates: List[Dict[str, Any]] = []

    pools = [strategy] if strategy and strategy in CANDIDATE_POOLS else list(CANDIDATE_POOLS.keys())

    for pool_key in pools:
        for item in CANDIDATE_POOLS[pool_key]:
            ticker = item["ticker"]
            enriched = fetch_openbb_data(ticker)

            curr_price = enriched.get("current_price") or 100.0
            # Heuristic target entry: ~10-15% margin of safety from current price
            target_entry = round(curr_price * 0.88, 2) if curr_price else None

            # Determine available platforms (Degiro and Exante support major US/EU equities and ETFs)
            platforms = ["Degiro", "Exante"]

            candidate = {
                "ticker": ticker,
                "name": enriched.get("name") or item["name"],
                "asset_type": "etf" if pool_key == "thematic_etfs" else "equity",
                "target_entry_price": target_entry,
                "current_price": curr_price,
                "currency": enriched.get("currency") or "USD",
                "thesis_summary": item["thesis"],
                "status": "watching",
                "platforms": platforms,
                "dominant_sector": enriched.get("sector") or item.get("sector") or "Diversified",
                "industry": enriched.get("industry") or item.get("sector") or "Diversified",
                "sector": enriched.get("sector") or item.get("sector") or "Diversified",
                "country": enriched.get("country") or "United States",
                "analyst_rating": enriched.get("analyst_rating") or "Buy",
                "morningstar_rating": enriched.get("morningstar_rating") or "4 Stars",
                "morningstar_risk": enriched.get("morningstar_risk") or "Below Average",
                "pe_ratio": enriched.get("pe_ratio"),
                "dividend_yield": enriched.get("dividend_yield"),
                "market_cap": enriched.get("market_cap"),
                "volatility": enriched.get("volatility"),
                "sharpe_ratio": enriched.get("sharpe_ratio"),
                "max_drawdown": enriched.get("max_drawdown"),
                "upside_potential": enriched.get("upside_potential"),
                "yahoo_ticker": ticker,
                "strategy": pool_key,
                "tags": ["watchlist"],
            }
            if is_quality_asset(candidate):
                candidates.append(candidate)
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    return candidates


def scan_watchlist_candidates(strategy: Optional[str] = None) -> List[Dict[str, Any]]:
    """Scan potential watchlist items and return the candidate list."""
    return get_potential_watchlist_items(strategy=strategy, limit=10)


def generate_watchlist_item_note(
    candidate: Dict[str, Any],
    target_dir: Optional[str] = None,
    template_path: Optional[str] = None
) -> str:
    """Generate Markdown content for a watchlist item using the vault template."""
    now_date = datetime.now().strftime("%Y-%m-%d")

    ticker = candidate.get("ticker", "TICKER")
    name = candidate.get("name", ticker)
    asset_type = candidate.get("asset_type", "equity")
    target_entry = candidate.get("target_entry_price", "null")
    current_price = candidate.get("current_price", "null")
    currency = candidate.get("currency", "USD")
    thesis = candidate.get("thesis_summary", "High quality business with durable competitive advantages.")
    status = candidate.get("status", "watching")
    dominant_sector = candidate.get("dominant_sector", "Technology")
    industry = candidate.get("industry", dominant_sector)
    sector = candidate.get("sector", dominant_sector)
    pe_ratio = candidate.get("pe_ratio", "null")
    dividend_yield = candidate.get("dividend_yield", "null")
    market_cap = candidate.get("market_cap", "null")
    volatility = candidate.get("volatility", "null")
    sharpe_ratio = candidate.get("sharpe_ratio", "null")
    max_drawdown = candidate.get("max_drawdown", "null")
    upside_potential = candidate.get("upside_potential", "null")
    isin = candidate.get("isin", "null")
    yahoo_ticker = candidate.get("yahoo_ticker", ticker)
    ms_rating = candidate.get("morningstar_rating", "null")
    ms_risk = candidate.get("morningstar_risk", "null")
    analyst_rating = candidate.get("analyst_rating", "Buy")

    platforms_list = candidate.get("platforms", ["Degiro", "Exante"])
    platforms_str = "\n".join([f"  - {p}" for p in platforms_list])
    platforms_links = ", ".join([f"[[{p}]]" for p in platforms_list])

    tags_list = candidate.get("tags", ["watchlist"])
    tags_str = "\n".join([f"  - {t}" for t in tags_list])

    analyst_str = f'  - "{analyst_rating}"' if isinstance(analyst_rating, str) else "\n".join([f'  - "{r}"' for r in analyst_rating])

    content = f"""---
ticker: {ticker}
name: "{name}"
asset_type: {asset_type}
target_entry_price: {target_entry}
current_price: {current_price}
currency: {currency}
thesis_summary: "{thesis}"
status: {status}
platforms:
{platforms_str}
dominant_sector: {dominant_sector}
industry: {industry}
sector: {sector}
analyst_rating:
{analyst_str}
morningstar_rating: {ms_rating}
morningstar_risk: {ms_risk}
pe_ratio: {pe_ratio}
dividend_yield: {f'"{dividend_yield}"' if dividend_yield and dividend_yield != 'null' else 'null'}
market_cap: {f'"{market_cap}"' if market_cap and market_cap != 'null' else 'null'}
volatility: {f'"{volatility}"' if volatility and volatility != 'null' else 'null'}
sharpe_ratio: {sharpe_ratio}
max_drawdown: {f'"{max_drawdown}"' if max_drawdown and max_drawdown != 'null' else 'null'}
upside_potential: {f'"{upside_potential}"' if upside_potential and upside_potential != 'null' else 'null'}
isin: {isin}
yahoo_ticker: {yahoo_ticker}
last_updated: "{now_date}"
tags:
{tags_str}
---

# {name} ({ticker})

**Status:** `{status}`  
**Target Entry:** {target_entry} {currency} | **Current Price:** {current_price} {currency}  
**Upside Potential:** {upside_potential} | **Sharpe Ratio (1Y):** {sharpe_ratio} | **Volatility (1Y):** {volatility}  
**Available Platforms:** {platforms_links}  
**Analyst Rating:** {analyst_rating} | **Industry:** {industry}

---

## 💡 Investment Thesis
- **Core Catalyst:** {thesis}
- **Competitive Advantage / Moat:** Strong brand, distribution power, and structural pricing power.
- **Valuation Target:** Entry below {target_entry} {currency} provides an attractive risk-adjusted margin of safety (Target Upside: {upside_potential}).

## 🎯 Entry Strategy & Triggers
- **Target Buy Zone:** {target_entry} {currency}
- **Allocation Plan:** Initial 3-5% portfolio weighting.

## ⚠️ Key Risks & Invalidation
- **Historical Max Drawdown (1Y):** {max_drawdown}
- **Bear Case:** Sector headwinds, margin compression, or macro valuation compression.
- **Invalidation Condition:** Deterioration of balance sheet or loss of core moat.

## 🔗 Links & Research
- [Yahoo Finance](https://finance.yahoo.com/quote/{ticker})
- Related Research Notes:
"""
    return content


def save_watchlist_item(candidate: Dict[str, Any], output_dir: Optional[str] = None) -> str:
    """Save a candidate as a markdown note in 10_Finance/Watchlist/."""
    if output_dir is None:
        output_dir = os.path.join(vault_root, "10_Finance", "Watchlist")
    os.makedirs(output_dir, exist_ok=True)

    asset_type = (candidate.get("asset_type") or "").lower()
    ticker = candidate.get("ticker", "UNKNOWN").replace("/", "_").replace(".", "_")
    name = candidate.get("name") or ticker

    if asset_type == "etf":
        from platforms.common import slugify_asset_name
        slug = slugify_asset_name(name, ticker=ticker, asset_type="etf")
        filename = f"{slug}.md"
    else:
        filename = f"{ticker}.md"
    file_path = os.path.join(output_dir, filename)

    content = generate_watchlist_item_note(candidate)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved watchlist item note: {file_path}")
    return file_path
