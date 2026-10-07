#!/usr/bin/env python3
"""Watchlist Discovery & Morningstar Enrichment CLI

Scans market opportunities across Quality Growth, Dividend Value, and Thematic ETFs,
enriches them with OpenBB / Morningstar / analyst ratings, and saves notes to 10_Finance/Watchlist/.
"""

import argparse
import os
import sys

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from integrations.openbb.service import (
    fetch_openbb_data,
    get_potential_watchlist_items,
    is_openbb_available,
    save_watchlist_item,
)


def print_table(candidates):
    if not candidates:
        print("No candidates found.")
        return

    header = f"{'Ticker':<8} | {'Name':<24} | {'Target':<10} | {'Price':<10} | {'Upside':<8} | {'Sharpe':<7} | {'Vol(1Y)':<8} | {'MaxDD':<8} | {'Rating':<11}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for c in candidates:
        ticker = c.get("ticker", "")
        name = (c.get("name", "")[:22] + "...") if len(c.get("name", "")) > 24 else c.get("name", "")
        tgt = f"{c.get('target_entry_price', '')} {c.get('currency', '')}"
        price = f"{c.get('current_price', '')} {c.get('currency', '')}"
        upside = str(c.get("upside_potential", "-")) if c.get("upside_potential") else "-"
        sharpe = str(c.get("sharpe_ratio", "-")) if c.get("sharpe_ratio") is not None else "-"
        vol = str(c.get("volatility", "-")) if c.get("volatility") else "-"
        maxdd = str(c.get("max_drawdown", "-")) if c.get("max_drawdown") else "-"
        rating = str(c.get("analyst_rating", "-")) if c.get("analyst_rating") else "-"
        print(
            f"{ticker:<8} | {name:<24} | {tgt:<10} | {price:<10} | {upside:<8} | {sharpe:<7} | {vol:<8} | {maxdd:<8} | {rating:<11}"
        )
    print("-" * len(header))


def main():
    parser = argparse.ArgumentParser(description="Discover watchlist candidates and generate notes.")
    parser.add_argument(
        "--strategy",
        choices=[
            "quality_growth",
            "dividend_value",
            "european_leaders",
            "dividend_aristocrats",
            "fallen_angels",
            "thematic_etfs",
            "all",
        ],
        default="all",
        help="Screening strategy",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of candidates to scan")
    parser.add_argument("--add", type=str, help="Single ticker symbol to enrich and add directly to watchlist")
    parser.add_argument(
        "--save-all", action="store_true", help="Save all scanned candidates as Markdown notes in 10_Finance/Watchlist"
    )

    args = parser.parse_args()

    print(
        f"OpenBB Integration Status: {'[AVAILABLE]' if is_openbb_available() else '[FALLBACK ACTIVE (yfinance/market data)]'}\n"
    )

    if args.add:
        sym = args.add.strip().upper()
        print(f"Enriching ticker: {sym}...")
        enriched = fetch_openbb_data(sym)
        curr_price = enriched.get("current_price") or 100.0
        target_entry = round(curr_price * 0.88, 2) if curr_price else None

        candidate = {
            "ticker": sym,
            "name": enriched.get("name") or sym,
            "asset_type": "equity",
            "target_entry_price": target_entry,
            "current_price": curr_price,
            "currency": enriched.get("currency") or "USD",
            "thesis_summary": f"Strong industry position in {enriched.get('sector', 'its sector')} with favorable fundamentals.",
            "status": "watching",
            "platforms": ["Degiro", "Exante"],
            "dominant_sector": enriched.get("sector") or "Technology",
            "industry": enriched.get("industry") or "Technology",
            "sector": enriched.get("sector") or "Technology",
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
            "yahoo_ticker": sym,
            "tags": ["watchlist"],
        }
        path = save_watchlist_item(candidate)
        print(f"\nSuccessfully added watchlist note: {path}")
        return

    strategy = None if args.strategy == "all" else args.strategy
    print(f"Scanning watchlist candidates (Strategy: {args.strategy}, Limit: {args.limit})...\n")
    candidates = get_potential_watchlist_items(strategy=strategy, limit=args.limit)
    print_table(candidates)

    if args.save_all:
        print("\nSaving candidate notes to 10_Finance/Watchlist/...")
        for c in candidates:
            save_watchlist_item(c)
        print(f"\nSaved {len(candidates)} watchlist items.")
    else:
        print("\nTip: To save candidates to notes, run with --save-all or use --add <TICKER>.")


if __name__ == "__main__":
    main()
