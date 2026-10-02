#!/usr/bin/env python3
"""Sync ETF Top Holdings, generate company notes in 10_Finance/ETF_Holdings/,

and update bi-directional links and exposure analytics across the vault.
"""

import os
import sys
import glob
import re
import argparse
import datetime
import concurrent.futures
from typing import Optional, Dict, Any, List, Set, Tuple

# Configure UTF-8 encoding for stdout/stderr on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure script root and integrations are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    import yaml
except ImportError:
    yaml = None

from model.asset import Asset
from platforms.common import get_max_workers
from ui_progress import create_progress
from integrations.justetf.service import fetch_justetf_top_holdings
from integrations.yfinance.service import (
    fetch_yfinance_top_holdings,
    fetch_company_fundamentals,
    search_yahoo_symbol
)
from integrations.sector_classifier import load_sector_config

DEFAULT_MAX_TOP_HOLDINGS = 10


def load_etf_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load ETF configuration from config.yaml."""
    candidate_paths = []
    if config_path:
        candidate_paths.append(config_path)

    system_dir = os.path.join(VAULT_ROOT, "99_System")
    candidate_paths.extend([
        os.path.join(system_dir, "config.yaml"),
        os.path.join(VAULT_ROOT, "config.yaml"),
    ])

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                loaded = yaml.safe_load(content) if yaml else None
                if isinstance(loaded, dict):
                    return loaded
            except Exception:
                pass
    return {}


def get_configured_max_holdings(config: Optional[Dict[str, Any]] = None) -> int:
    """Retrieve max_top_holdings from config or default."""
    if not config:
        config = load_etf_config()
    etf_cfg = config.get("etf", {})
    if isinstance(etf_cfg, dict) and "max_top_holdings" in etf_cfg:
        try:
            return int(etf_cfg["max_top_holdings"])
        except (ValueError, TypeError):
            pass
    return DEFAULT_MAX_TOP_HOLDINGS


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filenames."""
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean.replace(' ', '_')


def extract_holdings_for_etf(asset: Asset, limit: int = 10) -> List[Dict[str, Any]]:
    """Extract top holdings for an ETF by trying JustETF and yfinance sources."""
    holdings: List[Dict[str, Any]] = []

    # 1. Try Yahoo Finance first if yahoo_ticker or ticker is available
    symbols_to_try = []
    if asset.yahoo_ticker:
        symbols_to_try.append(asset.yahoo_ticker)
    if asset.ticker:
        symbols_to_try.append(asset.ticker.split('.')[0] if '.' in asset.ticker else asset.ticker)

    for sym in symbols_to_try:
        yf_holdings = fetch_yfinance_top_holdings(sym, limit=limit)
        if yf_holdings:
            holdings = yf_holdings
            break

    # 2. Try JustETF if yfinance produced no holdings or if ISIN is available
    if not holdings and asset.isin:
        je_holdings = fetch_justetf_top_holdings(asset.isin, limit=limit)
        if je_holdings:
            holdings = je_holdings

    # 3. If JustETF was used and tickers are missing, attempt ticker resolution
    standardized: List[Dict[str, Any]] = []
    for h in holdings[:limit]:
        t = h.get("ticker")
        n = h.get("name", "").strip()
        w = h.get("weight_pct", 0.0)

        if not t and n:
            # Try searching Yahoo symbol
            found = search_yahoo_symbol(n)
            if found:
                t = found
            else:
                t = sanitize_filename(n)
        elif not t:
            t = "UNKNOWN"

        standardized.append({
            "ticker": t,
            "name": n or t,
            "weight_pct": w
        })

    return standardized


def update_etf_asset_note(
    asset: Asset,
    file_path: str,
    holdings: List[Dict[str, Any]],
    dry_run: bool = False
) -> None:
    """Update ETF asset note with top_holdings in frontmatter and markdown body."""
    top_links = [f"[[{h['ticker']}]]" for h in holdings]
    asset.top_holdings = top_links

    # Construct markdown table for Top Holdings
    table_lines = [
        "## 📊 Top Holdings",
        "| Holding | Name | Weight (%) | Indirect Value (PLN) |",
        "| --- | --- | --- | --- |"
    ]
    etf_val = float(asset.value_pln or 0.0)
    for h in holdings:
        w = float(h.get("weight_pct", 0.0))
        indirect_pln = etf_val * (w / 100.0)
        indirect_str = f"{indirect_pln:,.2f} PLN" if indirect_pln > 0 else "-"
        table_lines.append(
            f"| [[{h['ticker']}]] | {h['name']} | {w:.2f}% | {indirect_str} |"
        )
    table_block = "\n".join(table_lines) + "\n"

    # Replace or append ## 📊 Top Holdings in body
    body = asset.body or ""
    if "## 📊 Top Holdings" in body:
        # Replace existing section up to next ## or end of file
        pattern = r"## 📊 Top Holdings\n.*?(?=\n## |\Z)"
        body = re.sub(pattern, table_block.strip(), body, flags=re.DOTALL)
    else:
        # Append before Investment Thesis or at the end
        if "## Investment Thesis / Notes" in body:
            body = body.replace("## Investment Thesis / Notes", f"{table_block}\n## Investment Thesis / Notes")
        else:
            body = f"{body.rstrip()}\n\n{table_block}"

    asset.body = body
    if not dry_run:
        asset.save(file_path)


def generate_holding_note(
    ticker: str,
    name: str,
    etf_exposures: List[Dict[str, Any]],
    direct_asset_note: Optional[str],
    watchlist_note: Optional[str],
    sector_config: Dict[str, Any],
    output_dir: str,
    dry_run: bool = False
) -> None:
    """Generate or update an individual ETF holding note in 10_Finance/ETF_Holdings/."""
    # Fetch fundamentals from Yahoo Finance
    fundamentals = fetch_company_fundamentals(ticker, fallback_name=name)
    company_name = fundamentals.get("name") or name or ticker
    if company_name == ticker and name and name != ticker:
        company_name = name

    sector = fundamentals.get("sector") or "Diversified"
    industry = fundamentals.get("industry") or sector
    country = fundamentals.get("country") or "Unknown"
    market_cap = fundamentals.get("market_cap")
    pe_ratio = fundamentals.get("pe_ratio")
    dividend_yield = fundamentals.get("dividend_yield")
    current_price = fundamentals.get("current_price")
    currency = fundamentals.get("currency") or "USD"

    # Map dominant sector
    dom_cfg = sector_config.get("dominant_sector", {})
    mappings_lower = {k.lower(): v for k, v in dom_cfg.get("mappings", {}).items()}
    dominant_sector = mappings_lower.get(str(sector).lower(), sector)

    # Calculate total indirect value in PLN
    total_indirect_pln = sum(float(e.get("indirect_pln", 0.0)) for e in etf_exposures)
    parent_etf_links = [f"[[{e.get('etf_note_name') or e['etf_ticker']}]]" for e in etf_exposures]

    # Build exposure table rows
    exposure_rows = []
    for e in etf_exposures:
        ind_pln = float(e.get("indirect_pln", 0.0))
        ind_str = f"{ind_pln:,.2f} PLN" if ind_pln > 0 else "-"
        etf_link = e.get('etf_note_name') or e['etf_ticker']
        exposure_rows.append(
            f"| [[{etf_link}]] | {e['etf_name']} | {e['weight_pct']:.2f}% | {ind_str} |"
        )
    exposure_table = "\n".join(exposure_rows)

    direct_badge = f"✅ Yes ([[{direct_asset_note}]])" if direct_asset_note else "❌ No"
    direct_asset_val = f'"[[{direct_asset_note}]]"' if direct_asset_note else "null"

    wl_badge = f"👁️ Watching ([[{watchlist_note}]])" if watchlist_note else "-"
    wl_val = f'"[[{watchlist_note}]]"' if watchlist_note else "null"

    today_str = datetime.date.today().isoformat()

    # Safe YAML name
    safe_name = f'"{company_name}"' if any(c in company_name for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '"']) else company_name

    content = f"""---
ticker: {ticker}
name: {safe_name}
asset_type: etf_holding
dominant_sector: {dominant_sector}
sector: {sector}
industry: {industry}
country: {country}
market_cap: {market_cap if market_cap else "null"}
pe_ratio: {pe_ratio if pe_ratio is not None else "null"}
dividend_yield: {dividend_yield if dividend_yield else "null"}
current_price: {current_price if current_price is not None else "null"}
currency: {currency}
parent_etfs:
"""
    for petf in parent_etf_links:
        content += f'  - "{petf}"\n'

    content += f"""total_indirect_value_pln: {round(total_indirect_pln, 2)}
direct_asset: {direct_asset_val}
watchlist_note: {wl_val}
last_updated: "{today_str}"
tags:
  - etf_holding
---

# {company_name} ({ticker})

**Direct Holding in Portfolio:** {direct_badge} | **Watchlist:** {wl_badge}  
**Sector:** {sector} | **Industry:** {industry} | **Country:** {country}  
**Market Cap:** {market_cap or "-"} | **P/E Ratio:** {pe_ratio or "-"} | **Dividend Yield:** {dividend_yield or "-"}

---

## 📊 ETF Exposure & Weight
| ETF | ETF Name | Holding Weight (%) | Indirect Value (PLN) |
| --- | --- | --- | --- |
{exposure_table}

## 💡 Notes & Analysis
Tracked underlying holding across portfolio ETFs.
"""

    out_file = os.path.join(output_dir, f"{sanitize_filename(ticker)}.md")
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)



def generate_overview_dashboard(output_file: str, dry_run: bool = False) -> None:
    """Create or update 10_Finance/ETF_Holdings/Holdings_Overview.md dashboard."""
    content = r"""---
type: dashboard
title: ETF Underlying Holdings & Overlap Overview
last_updated: "{{date}}"
tags:
  - dashboard
  - etf_holding
---

# 🌐 ETF Underlying Holdings & Overlap Overview

This dashboard aggregates underlying companies held within portfolio ETFs, calculates combined indirect exposure, and identifies portfolio concentration and overlap risks.

---

## 🏆 Top Underlying Holdings by Total Indirect Exposure

```dataviewjs
let pages = dv.pages('"10_Finance/ETF_Holdings"')
    .where(p => p.asset_type === "etf_holding" && p.file.name !== "Holdings_Overview");

let rows = pages.map(p => {
    let parentCount = Array.isArray(p.parent_etfs) ? p.parent_etfs.length : (p.parent_etfs ? 1 : 0);
    let indirectPln = p.total_indirect_value_pln || 0;
    let directBadge = p.direct_asset ? `✅ Yes (${p.direct_asset})` : "❌ No";
    let peStr = p.pe_ratio !== null && p.pe_ratio !== undefined ? p.pe_ratio : "-";
    let mcapStr = p.market_cap || "-";
    
    return [
        p.file.link,
        p.name || p.ticker,
        p.dominant_sector || p.sector || "-",
        p.country || "-",
        parentCount,
        peStr,
        mcapStr,
        directBadge,
        indirectPln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN"
    ];
}).sort(r => -parseFloat(r[8].replace(/,/g, '').replace(' PLN', '')));

dv.table(
    ["Ticker / Link", "Company Name", "Sector", "Country", "In # ETFs", "P/E", "Market Cap", "Direct Holding?", "Indirect Value (PLN)"],
    rows
);
```

---

## 🔄 ETF Overlap Matrix (Held in 2+ ETFs)

```dataviewjs
let pages = dv.pages('"10_Finance/ETF_Holdings"')
    .where(p => p.asset_type === "etf_holding" && p.file.name !== "Holdings_Overview");

let overlapped = pages.filter(p => {
    let parents = Array.isArray(p.parent_etfs) ? p.parent_etfs : (p.parent_etfs ? [p.parent_etfs] : []);
    return parents.length >= 2;
});

let overlapRows = overlapped.map(p => {
    let parents = Array.isArray(p.parent_etfs) ? p.parent_etfs.join(", ") : p.parent_etfs;
    let indirectPln = p.total_indirect_value_pln || 0;
    return [
        p.file.link,
        p.name || p.ticker,
        parents,
        p.dominant_sector || p.sector || "-",
        indirectPln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN"
    ];
}).sort(r => -parseFloat(r[4].replace(/,/g, '').replace(' PLN', '')));

if (overlapRows.length > 0) {
    dv.table(["Company", "Name", "Found In ETFs", "Sector", "Total Indirect Value"], overlapRows);
} else {
    dv.paragraph("ℹ️ *No companies are currently held across multiple ETFs.*");
}
```

---

## 🎯 Cross-Exposure: Single Stocks Owned Directly & In ETFs

```dataviewjs
let holdings = dv.pages('"10_Finance/ETF_Holdings"')
    .where(p => p.asset_type === "etf_holding" && p.direct_asset);

let crossRows = holdings.map(p => {
    let directPage = dv.page(p.direct_asset);
    let directPln = directPage ? (directPage.value_pln || 0) : 0;
    let indirectPln = p.total_indirect_value_pln || 0;
    let totalExposure = directPln + indirectPln;
    
    return [
        p.file.link,
        p.name,
        p.direct_asset,
        directPln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN",
        indirectPln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN",
        `**${totalExposure.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN**`
    ];
}).sort(r => -parseFloat(r[5].replace(/\*\*/g, '').replace(/,/g, '').replace(' PLN', '')));

if (crossRows.length > 0) {
    dv.table(
        ["Company", "Name", "Direct Asset Note", "Direct Value (PLN)", "Indirect Value (PLN)", "Total Exposure (PLN)"],
        crossRows
    );
} else {
    dv.paragraph("ℹ️ *No direct stock holdings currently overlap with ETF holdings.*");
}
```
"""
    today_str = datetime.date.today().isoformat()
    content = content.replace('{{date}}', today_str)

    if not dry_run:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)


def sync_all_etfs(
    assets_dir: str,
    holdings_dir: str,
    target_etf: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    max_workers: Optional[int] = None,
    show_progress: bool = True,
) -> None:
    """Main synchronization routine."""
    config = load_etf_config()
    max_holdings = limit if limit is not None else get_configured_max_holdings(config)
    sector_config = load_sector_config()
    workers = get_max_workers(max_workers, base_dir=VAULT_ROOT)

    print(f"🚀 Starting ETF Top Holdings Sync (Max holdings per ETF: {max_holdings}, Workers: {workers}, Dry-run: {dry_run})")

    # 1. Load all direct assets to create a lookup map
    direct_assets: Dict[str, Asset] = {}
    etf_assets: List[Tuple[str, Asset]] = []

    asset_files = glob.glob(os.path.join(assets_dir, "*.md"))
    for af in asset_files:
        try:
            asset = Asset.from_file(af)
            note_name = os.path.splitext(os.path.basename(af))[0]
            if asset.asset_type == "etf":
                if target_etf is None or target_etf.lower() in [
                    asset.ticker.lower(),
                    (asset.isin or "").lower(),
                    (asset.yahoo_ticker or "").lower(),
                    os.path.basename(af).lower(),
                    note_name.lower()
                ]:
                    etf_assets.append((af, asset))
            else:
                # Direct stock or cash: map to note name for Obsidian wikilinks
                if asset.ticker:
                    direct_assets[asset.ticker.upper()] = note_name
                if asset.isin:
                    direct_assets[asset.isin.upper()] = note_name
                if asset.yahoo_ticker:
                    direct_assets[asset.yahoo_ticker.upper()] = note_name
                if asset.name:
                    direct_assets[asset.name.upper()] = note_name
        except Exception as e:
            sys.stderr.write(f"Error reading asset {af}: {e}\n")

    print(f"📦 Found {len(etf_assets)} ETF(s) to process and {len(direct_assets)} direct asset references.")

    # 2. Process each ETF and aggregate holdings concurrently
    # holding_map: ticker -> {"name": str, "exposures": [{"etf_note_name": ..., "etf_ticker": ..., "weight_pct": ..., "indirect_pln": ...}]}
    holding_map: Dict[str, Dict[str, Any]] = {}

    def _process_single_etf(item: Tuple[str, Asset]) -> Tuple[Asset, str, List[Dict[str, Any]]]:
        file_path, asset = item
        etf_note_name = os.path.splitext(os.path.basename(file_path))[0]
        if not show_progress:
            print(f"\n🔍 Processing ETF: {asset.ticker} ({asset.name}) | ISIN: {asset.isin} | Yahoo: {asset.yahoo_ticker}")
        holdings = extract_holdings_for_etf(asset, limit=max_holdings)
        if not show_progress:
            print(f"   Found {len(holdings)} holdings for {asset.ticker}:")
            for h in holdings:
                print(f"     - {h['ticker']}: {h['name']} ({h['weight_pct']}%)")
        update_etf_asset_note(asset, file_path, holdings, dry_run=dry_run)
        return asset, etf_note_name, holdings

    if etf_assets:
        print(f"⚡ Processing {len(etf_assets)} ETF(s) concurrently across {min(workers, len(etf_assets))} worker threads...")
        with create_progress(disable=not show_progress) as progress:
            task_etfs = progress.add_task(
                "[bold cyan]Decomposing ETF holdings[/bold cyan]",
                total=len(etf_assets),
                status="Starting...",
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_etf = {executor.submit(_process_single_etf, item): item for item in etf_assets}
                for future in concurrent.futures.as_completed(future_to_etf):
                    item = future_to_etf[future]
                    asset_item = item[1]
                    try:
                        asset, etf_note_name, holdings = future.result()
                        # Aggregate exposure
                        etf_val = float(asset.value_pln or 0.0)
                        for h in holdings:
                            t = h["ticker"].upper()
                            w = float(h.get("weight_pct", 0.0))
                            indirect_pln = etf_val * (w / 100.0)

                            if t not in holding_map:
                                holding_map[t] = {
                                    "ticker": h["ticker"],
                                    "name": h["name"],
                                    "exposures": []
                                }
                            holding_map[t]["exposures"].append({
                                "etf_note_name": etf_note_name,
                                "etf_ticker": asset.ticker,
                                "etf_name": asset.name,
                                "weight_pct": w,
                                "indirect_pln": indirect_pln
                            })
                        progress.update(task_etfs, advance=1, status=f"[green]✓[/green] {asset.ticker} ({len(holdings)} holdings)")
                    except Exception as e:
                        progress.update(task_etfs, advance=1, status=f"[red]✗[/red] {asset_item.ticker}")
                        if hasattr(progress, "console") and progress.console:
                            progress.console.print(f"[red]Error processing ETF {asset_item.ticker}:[/red] {e}")
                        else:
                            sys.stderr.write(f"Error processing ETF {asset_item.ticker}: {e}\n")

            progress.update(task_etfs, status="[bold green]Completed[/bold green]")

    # Load Watchlist notes for cross-referencing
    watchlist_dir = os.path.join(VAULT_ROOT, "10_Finance/Watchlist")
    watchlist_map: Dict[str, str] = {}
    if os.path.exists(watchlist_dir):
        for wf in glob.glob(os.path.join(watchlist_dir, "*.md")):
            base_name = os.path.splitext(os.path.basename(wf))[0]
            if base_name != "Watchlist":
                watchlist_map[base_name.upper()] = base_name
                try:
                    with open(wf, "r", encoding="utf-8") as f:
                        txt = f.read()
                    m = re.search(r'ticker:\s*([^\n\r]+)', txt)
                    if m:
                        watchlist_map[m.group(1).strip().strip('"\'').upper()] = base_name
                except Exception:
                    pass

    # 3. Generate or update holding notes concurrently
    if holding_map:
        print(f"\n📝 Generating/Updating {len(holding_map)} ETF holding notes in {holdings_dir} across {workers} worker threads...")

        def _process_single_holding(item: Tuple[str, Dict[str, Any]]):
            ticker, hdata = item
            direct_asset_note = None
            t_clean = ticker.upper()
            base_t = t_clean.split('.')[0]
            if t_clean in direct_assets:
                direct_asset_note = direct_assets[t_clean]
            elif base_t in direct_assets:
                direct_asset_note = direct_assets[base_t]

            watchlist_note = watchlist_map.get(t_clean) or watchlist_map.get(base_t)

            generate_holding_note(
                ticker=hdata["ticker"],
                name=hdata["name"],
                etf_exposures=hdata["exposures"],
                direct_asset_note=direct_asset_note,
                watchlist_note=watchlist_note,
                sector_config=sector_config,
                output_dir=holdings_dir,
                dry_run=dry_run
            )

        with create_progress(disable=not show_progress) as progress:
            task_holdings = progress.add_task(
                "[bold cyan]Generating ETF holding notes[/bold cyan]",
                total=len(holding_map),
                status="Starting...",
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_holding = {executor.submit(_process_single_holding, item): item for item in holding_map.items()}
                for future in concurrent.futures.as_completed(future_to_holding):
                    item = future_to_holding[future]
                    ticker = item[0]
                    try:
                        future.result()
                        progress.update(task_holdings, advance=1, status=f"[green]✓[/green] {ticker}")
                    except Exception as e:
                        progress.update(task_holdings, advance=1, status=f"[red]✗[/red] {ticker}")
                        if hasattr(progress, "console") and progress.console:
                            progress.console.print(f"[red]Error generating holding note for {ticker}:[/red] {e}")
                        else:
                            sys.stderr.write(f"Error generating holding note for {ticker}: {e}\n")

            progress.update(task_holdings, status="[bold green]Completed[/bold green]")

    # 4. Generate/Update Overview Dashboard
    overview_file = os.path.join(holdings_dir, "Holdings_Overview.md")
    print(f"📊 Updating dashboard: {overview_file}")
    generate_overview_dashboard(overview_file, dry_run=dry_run)

    print("\n✅ ETF Top Holdings Synchronization complete!")


def main():
    parser = argparse.ArgumentParser(description="Synchronize ETF top holdings and exposure analytics across the vault.")
    parser.add_argument("--etf", type=str, default=None, help="Sync specific ETF by ticker, ISIN, or file path.")
    parser.add_argument("--limit", type=int, default=None, help="Override maximum top holdings count.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of concurrent worker threads.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate run without writing files.")
    parser.add_argument("--no-progress", dest="no_progress", action="store_true", default=False, help="Disable interactive rich progress bars.")
    parser.add_argument("--assets-dir", type=str, default=os.path.join(VAULT_ROOT, "10_Finance/Assets"), help="Path to Assets directory.")
    parser.add_argument("--holdings-dir", type=str, default=os.path.join(VAULT_ROOT, "10_Finance/ETF_Holdings"), help="Path to ETF_Holdings directory.")

    args = parser.parse_args()
    sync_all_etfs(
        assets_dir=args.assets_dir,
        holdings_dir=args.holdings_dir,
        target_etf=args.etf,
        limit=args.limit,
        dry_run=args.dry_run,
        max_workers=args.max_workers,
        show_progress=not args.no_progress,
    )


if __name__ == "__main__":
    main()
