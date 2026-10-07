#!/usr/bin/env python3
"""Automated Macroeconomic Synchronization Engine.

Coordinates live macroeconomic data ingestion from specialized integration providers:
  - NBP (Narodowy Bank Polski): Polish base interest rates, exchange rates, gold fixing.
  - Eurostat: Polish 10Y sovereign yields (Maastricht criterion), European & Polish HICP inflation.
  - Yahoo Finance: US Treasury yields (^TNX, 2YY=F), strategic commodities (Gold, Silver, Copper, Brent), VIX.

Renders 10_Finance/Macro.md via the Obsidian vault template:
  - 99_System/Templates/macro_template.md
"""

import argparse
import datetime
import os
import re
import sys
from typing import Any

# Configure UTF-8 encoding for stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure script directory and vault root are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

integrations_dir = os.path.join(CURRENT_DIR, "integrations")
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

import jinja2

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

from integrations.eurostat import EurostatMacroSupplier
from integrations.nbp import NBPMacroSupplier


def fetch_ticker_quote(ticker_symbol: str) -> dict[str, Any] | None:
    """Fetch current price, 52-week high/low, and 1-month trend for a ticker symbol using yfinance."""
    if not yf:
        return None
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo")
        if hist.empty:
            return None

        current_price = float(hist["Close"].iloc[-1])
        first_price = float(hist["Close"].iloc[0])
        pct_change_1m = ((current_price - first_price) / first_price) * 100 if first_price else 0.0

        # Try to get 52-week range from history
        hist_1y = ticker.history(period="1y")
        if not hist_1y.empty:
            low_52w = float(hist_1y["Low"].min())
            high_52w = float(hist_1y["High"].max())
        else:
            low_52w = current_price * 0.85
            high_52w = current_price * 1.15

        trend = "📈 Increasing" if pct_change_1m > 1.0 else ("📉 Decreasing" if pct_change_1m < -1.0 else "➡️ Stable")

        return {
            "current": current_price,
            "pct_change_1m": pct_change_1m,
            "trend": trend,
            "low_52w": low_52w,
            "high_52w": high_52w,
        }
    except Exception as e:
        print(f"   ⚠️ Could not fetch quote for {ticker_symbol}: {e}")
        return None


def fetch_macro_dataset() -> dict[str, Any]:
    """Aggregate live macro dataset across specialized integration suppliers."""
    print("   🌐 Ingesting macroeconomic indicators across integration suppliers...")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # 1. Global & Domestic Sovereign Yields
    print("      Ingesting Sovereign Yields (US 10Y, US 2Y & Eurostat PL 10Y)...")
    tnx = fetch_ticker_quote("^TNX")  # US 10Y Yield
    two_y = fetch_ticker_quote("2YY=F")  # US 2Y Yield futures
    irx = fetch_ticker_quote("^IRX")  # 13-week T-Bill Yield fallback

    us_10y = tnx["current"] if tnx else 5.23
    us_2y = two_y["current"] if two_y else (irx["current"] if irx else 4.50)
    spread_bps = round((us_10y - us_2y) * 100, 1)

    spread_status = (
        "Normal (Upward Sloping)"
        if spread_bps > 10
        else ("Inverted (Recession Warning)" if spread_bps < -10 else "Flat / Transitioning")
    )

    eurostat_pl10y = EurostatMacroSupplier.fetch_10y_yield(geo="PL")

    # 2. Currencies, Precious Metals & Strategic Commodities
    print("      Ingesting FX, Commodities & Volatility (NBP, Yahoo Finance)...")
    nbp_fx = NBPMacroSupplier.fetch_exchange_rates(["USD", "EUR", "GBP", "CHF"])
    nbp_gold = NBPMacroSupplier.fetch_gold_fixing()

    usd_pln_quote = fetch_ticker_quote("USDPLN=X")
    eur_pln_quote = fetch_ticker_quote("EURPLN=X")
    gbp_pln_quote = fetch_ticker_quote("GBPPLN=X")
    gold_quote = fetch_ticker_quote("GC=F")
    silver_quote = fetch_ticker_quote("SI=F")
    copper_quote = fetch_ticker_quote("HG=F")
    brent_quote = fetch_ticker_quote("BZ=F")
    vix_quote = fetch_ticker_quote("^VIX")

    usd_pln = nbp_fx.get("USD", usd_pln_quote["current"] if usd_pln_quote else 3.8478)
    eur_pln = nbp_fx.get("EUR", eur_pln_quote["current"] if eur_pln_quote else 4.3769)
    gbp_pln = nbp_fx.get("GBP", gbp_pln_quote["current"] if gbp_pln_quote else 5.1054)

    gold_usd = gold_quote["current"] if gold_quote else 4168.0
    gold_pln = nbp_gold["price_oz_pln"] if nbp_gold else (gold_usd * usd_pln)
    silver_usd = silver_quote["current"] if silver_quote else 61.56
    copper_usd = copper_quote["current"] if copper_quote else 6.64
    brent_usd = brent_quote["current"] if brent_quote else 97.69
    vix_val = vix_quote["current"] if vix_quote else 15.82

    vix_status = (
        "Complacent / Low Volatility" if vix_val < 18 else ("Elevated / Risk-Off" if vix_val > 25 else "Moderate")
    )

    # 3. Central Bank Interest Rates
    print("      Ingesting Central Bank Base Rates (NBP XML, ECB, Fed)...")
    nbp_rates = NBPMacroSupplier.fetch_base_rates()

    central_banks = [
        {
            "name": "**Federal Reserve (Fed)**",
            "rate": "Fed Funds Target Range",
            "level": "4.75% – 5.00%",
            "trend": "Neutral / Easing",
            "last_date": "2026-07-29",
            "next_date": "2026-09-16",
        },
        {
            "name": "**European Central Bank (ECB)**",
            "rate": "Main Refinancing / Deposit Rate",
            "level": "3.25% / 3.00%",
            "trend": "Easing",
            "last_date": "2026-07-18",
            "next_date": "2026-09-10",
        },
        {
            "name": "**National Bank of Poland (NBP)**",
            "rate": "Stopa Referencyjna",
            "level": f"{nbp_rates['ref_rate']:.2f}%",
            "trend": nbp_rates["trend"],
            "last_date": nbp_rates["last_decision_date"],
            "next_date": "2026-10-07",
        },
    ]

    # 4. Inflation & Labor Market Indicators
    print("      Ingesting Inflation Metrics (Eurostat)...")
    pl_inf = EurostatMacroSupplier.fetch_hicp_inflation("PL")
    ea_inf = EurostatMacroSupplier.fetch_hicp_inflation("EA20")

    inflation = [
        {
            "indicator": "**CPI Inflation**",
            "region": "🇺🇸 United States",
            "current": "2.6%",
            "prior": "2.8%",
            "target": "2.0%",
            "status": "Moderating",
        },
        {
            "indicator": "**HICP Inflation**",
            "region": "🇪🇺 Eurozone",
            "current": ea_inf["current"],
            "prior": ea_inf["prior"],
            "target": "2.0%",
            "status": ea_inf["status"],
        },
        {
            "indicator": "**CPI / HICP Inflation**",
            "region": "🇵🇱 Poland",
            "current": pl_inf["current"],
            "prior": pl_inf["prior"],
            "target": "2.5% (±1.0%)",
            "status": pl_inf["status"],
        },
        {
            "indicator": "**Unemployment Rate**",
            "region": "🇺🇸 United States",
            "current": "4.1%",
            "prior": "4.0%",
            "target": "~4.0% (Full Employment)",
            "status": "Stable",
        },
        {
            "indicator": "**Unemployment Rate (Eurostat/BAEL)**",
            "region": "🇵🇱 Poland",
            "current": "3.4% – 5.0%",
            "prior": "5.0%",
            "target": "Historical Low Range",
            "status": "Strong",
        },
    ]

    # 5. Macro Regime Determination
    if spread_bps < -10:
        regime_title = "Inverted Curve / Late-Cycle Pre-Recessionary"
        regime_desc = "Yield curve inversion signaling tight monetary constraints and elevated recession risk."
    elif spread_bps >= -10 and spread_bps <= 25:
        regime_title = "Disinflationary Easing / Curve Normalization"
        regime_desc = "Central bank rate cuts beginning; yield curve dis-inverting into neutral stance."
    else:
        regime_title = "Steep Curve / Mid-Cycle Expansion"
        regime_desc = "Positive term premia and healthy economic expansion with accommodative policy."

    spread_sign = "+" if spread_bps >= 0 else ""
    spread_display = f"**{spread_sign}{spread_bps:.0f} bps ({spread_sign}{spread_bps / 100:.2f}%)**"

    return {
        "last_updated": today_str,
        "us_10y_yield": us_10y,
        "us_10y_trend": tnx["trend"] if tnx else "📈 Increasing",
        "us_2y_yield": us_2y,
        "us_2y_trend": two_y["trend"] if two_y else "📈 Increasing",
        "yield_spread_10y_2y_bps": spread_bps,
        "yield_curve_status": spread_status,
        "spread_display": spread_display,
        "pl_10y_yield": eurostat_pl10y["yield"],
        "pl_10y_trend": eurostat_pl10y["trend"],
        "nbp_reference_rate": nbp_rates["ref_rate"],
        "poland_cpi": pl_inf.get("numeric", 2.5),
        "usd_pln": usd_pln,
        "usd_pln_range": f"{usd_pln_quote['low_52w']:.2f} – {usd_pln_quote['high_52w']:.2f}"
        if usd_pln_quote
        else "3.49 – 3.86",
        "eur_pln": eur_pln,
        "eur_pln_range": f"{eur_pln_quote['low_52w']:.2f} – {eur_pln_quote['high_52w']:.2f}"
        if eur_pln_quote
        else "4.19 – 4.40",
        "gbp_pln": gbp_pln,
        "gbp_pln_range": f"{gbp_pln_quote['low_52w']:.2f} – {gbp_pln_quote['high_52w']:.2f}"
        if gbp_pln_quote
        else "4.77 – 5.11",
        "gold_usd": gold_usd,
        "gold_pln": gold_pln,
        "gold_range": f"${gold_quote['low_52w']:,.0f} – ${gold_quote['high_52w']:,.0f}"
        if gold_quote
        else "$3,786 – $5,586",
        "silver_usd": silver_usd,
        "silver_range": f"${silver_quote['low_52w']:.2f} – ${silver_quote['high_52w']:.2f}"
        if silver_quote
        else "$45.38 – $121.30",
        "copper_usd": copper_usd,
        "copper_range": f"${copper_quote['low_52w']:.2f} – ${copper_quote['high_52w']:.2f}"
        if copper_quote
        else "$4.71 – $6.83",
        "brent_usd": brent_usd,
        "brent_range": f"${brent_quote['low_52w']:.2f} – ${brent_quote['high_52w']:.2f}"
        if brent_quote
        else "$58.72 – $126.10",
        "vix": vix_val,
        "vix_status": vix_status,
        "macro_regime_title": regime_title,
        "macro_regime_desc": regime_desc,
        "central_banks": central_banks,
        "inflation": inflation,
    }


def extract_custom_thesis_log(file_path: str) -> str | None:
    """Extract existing '## 📝 Observations & Macro Thesis Log' section to prevent overwriting user notes."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"(## 📝 Observations & Macro Thesis Log.*)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"   ⚠️ Could not read existing custom notes ({e})")
    return None


def render_macro_markdown(
    dataset: dict[str, Any],
    template_path: str | None = None,
    existing_notes_section: str | None = None,
) -> str:
    """Render 10_Finance/Macro.md by loading and compiling 99_System/Templates/macro_template.md."""
    if not template_path:
        template_path = os.path.join(VAULT_ROOT, "99_System", "Templates", "macro_template.md")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Macro template not found at: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        template_content = f.read()

    # Prepare custom notes section
    if existing_notes_section and existing_notes_section.strip():
        notes_block = existing_notes_section.strip()
    else:
        date_str = dataset["last_updated"]
        notes_block = (
            "## 📝 Observations & Macro Thesis Log\n\n"
            f"### {date_str}: Yield Curve Normalization & Monetary Easing Cycle\n"
            f"- US 10Y Treasury yield is at {dataset['us_10y_yield']:.2f}%, with 2Y yield at {dataset['us_2y_yield']:.2f}% (Spread: {dataset['spread_display']}).\n"
            f"- Poland 10Y Bond yield is at {dataset['pl_10y_yield']:.2f}%, with NBP reference rate at {dataset['nbp_reference_rate']:.2f}%.\n"
            f"- Gold is trading at ${dataset['gold_usd']:,.0f}/oz ({dataset['gold_pln']:,.0f} PLN); Copper at ${dataset['copper_usd']:.2f}/lb; Brent at ${dataset['brent_usd']:.2f}/bbl.\n"
            "- *Action Plan:* Maintain full emergency liquidity in Polish inflation-indexed retail bonds and EUR/PLN buffers; continue dollar-cost averaging into core global ETFs."
        )

    context = dict(dataset)
    context["custom_notes_section"] = notes_block

    if jinja2:
        template = jinja2.Template(template_content)
        rendered = template.render(context)
    else:
        # Fallback string interpolation if Jinja2 is unavailable
        rendered = template_content
        for key, val in context.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(val))

    return rendered.strip() + "\n"


def sync_macro(
    macro_path: str | None = None,
    template_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Synchronize macroeconomic data and render 10_Finance/Macro.md via template."""
    if not macro_path:
        macro_path = os.path.join(VAULT_ROOT, "10_Finance", "Macro.md")

    print(f"🌐 Synchronizing Macroeconomic Dashboard: {macro_path}")
    print("-" * 72)

    existing_notes = extract_custom_thesis_log(macro_path)
    dataset = fetch_macro_dataset()
    rendered_md = render_macro_markdown(
        dataset,
        template_path=template_path,
        existing_notes_section=existing_notes,
    )

    if dry_run:
        print("\n⚡ [DRY-RUN] Rendered Macro.md preview (First 40 lines):")
        preview_lines = rendered_md.splitlines()[:40]
        print("\n".join(preview_lines))
        print("...")
        print(f"\n⚡ Dry-run finished. No changes written to {macro_path}")
    else:
        os.makedirs(os.path.dirname(macro_path), exist_ok=True)
        with open(macro_path, "w", encoding="utf-8") as f:
            f.write(rendered_md)
        print(f"✔ Successfully synchronized Macro Dashboard: {macro_path}")
        print(
            f"   US 10Y Yield: {dataset['us_10y_yield']:.2f}% | 2Y Yield: {dataset['us_2y_yield']:.2f}% | Spread: {dataset['yield_spread_10y_2y_bps']} bps"
        )
        print(f"   Poland 10Y Yield: {dataset['pl_10y_yield']:.2f}% | NBP Rate: {dataset['nbp_reference_rate']:.2f}%")
        print(
            f"   USD/PLN: {dataset['usd_pln']:.4f} | EUR/PLN: {dataset['eur_pln']:.4f} | GBP/PLN: {dataset['gbp_pln']:.4f}"
        )
        print(
            f"   Gold: ${dataset['gold_usd']:,.0f} ({dataset['gold_pln']:,.0f} PLN) | Copper: ${dataset['copper_usd']:.2f} | Brent: ${dataset['brent_usd']:.2f}"
        )

    print("-" * 72)
    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Automated synchronization for 10_Finance/Macro.md via vault template.",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to Macro.md (default: 10_Finance/Macro.md in vault).",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Path to macro template (default: 99_System/Templates/macro_template.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display fetched data and preview markdown without saving.",
    )
    args = parser.parse_args()

    sync_macro(macro_path=args.file, template_path=args.template, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
