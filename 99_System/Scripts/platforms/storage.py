"""Asset note persistence, concurrency, and platform synchronization storage engine."""

import concurrent.futures
import os
import re
import sys
import threading
from datetime import datetime
from typing import Any

# Ensure script root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from integrations.multi_source_asset_enricher import MultiSourceAssetEnricher
from model.asset import Asset
from ui_progress import create_progress

from platforms.template import _inject_issuer_link, _inject_justetf_link, render_template_body

_asset_enricher = MultiSourceAssetEnricher()
_concurrency_lock = threading.Lock()


def save_or_update_asset(
    vault_assets_dir: str,
    platform: str,
    ticker: str,
    name: str,
    quantity: int | float,
    current_price: int | float,
    currency: str,
    avg_price: int | float | None = None,
    isin: str | None = None,
    current_date: str | None = None,
    template_fm: dict[str, Any] | None = None,
    template_body: str | None = None,
    source: str = "platform",
    portfolio: str | None = None,
    tags: list[str] | None = None,
    yahoo_ticker: str | None = None,
    asset_allocation: dict[str, Any] | None = None,
    asset_type: str | None = None,
    dominant_sector: str | None = None,
    industry: str | None = None,
    sector: str | None = None,
    stooq_ticker: str | None = None,
    country: str | None = None,
) -> str:
    """Enrich financial data, create or update asset note in 10_Finance/Assets, and return file path."""
    from platforms.common import (
        clean_asset_display_name,
        determine_asset_type,
        determine_issuer,
        determine_portfolio,
        sanitize_filename,
        slugify_asset_name,
    )

    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    # Clean and resolve display name
    display_name = clean_asset_display_name(name, isin=isin, ticker=ticker)
    name = display_name

    target_slug = slugify_asset_name(name=name, ticker=ticker, platform=platform, asset_type=asset_type, isin=isin)
    target_file_path = os.path.join(vault_assets_dir, f"{target_slug}.md")

    # Locate existing note
    file_path = None
    if os.path.exists(target_file_path):
        file_path = target_file_path
    else:
        # Check alternative legacy filenames
        safe_ticker = sanitize_filename(ticker)
        legacy_ticker_path = os.path.join(vault_assets_dir, f"{safe_ticker}.md")
        if os.path.exists(legacy_ticker_path):
            file_path = legacy_ticker_path
        else:
            legacy_name_path = os.path.join(vault_assets_dir, f"{sanitize_filename(name)}.md")
            if os.path.exists(legacy_name_path):
                file_path = legacy_name_path

    # If still not found, check existing notes by frontmatter ticker or isin within same platform and account type
    if not file_path and os.path.exists(vault_assets_dir):
        t_clean = (ticker or "").strip().lower()
        isin_clean = (isin or "").strip().lower() if isin else None
        target_plat = (platform or "").strip().lower()
        for fname in os.listdir(vault_assets_dir):
            if not fname.endswith(".md"):
                continue
            cand_path = os.path.join(vault_assets_dir, fname)
            try:
                cand_asset = Asset.from_file(cand_path)
                cand_plat = (cand_asset.platform or "").strip().lower()
                cand_t = (cand_asset.ticker or "").strip().lower()
                cand_isin = (cand_asset.isin or "").strip().lower() if cand_asset.isin else None

                # CRITICAL: Do NOT match an asset from a different platform!
                if target_plat and cand_plat and target_plat != cand_plat:
                    continue

                # Account suffix protection: match _ikze or _ike if present
                if t_clean.endswith(("_ikze", "_ike")) and not cand_t.endswith(("_ikze", "_ike")):
                    continue
                if not t_clean.endswith(("_ikze", "_ike")) and cand_t.endswith(("_ikze", "_ike")):
                    continue

                if (t_clean and cand_t == t_clean) or (isin_clean and cand_isin == isin_clean):
                    file_path = cand_path
                    break
            except Exception:
                continue

    # Auto-rename legacy ticker note to clean target slug if needed
    if (
        file_path
        and file_path != target_file_path
        and os.path.exists(file_path)
        and not os.path.exists(target_file_path)
    ):
        try:
            os.rename(file_path, target_file_path)
            print(f"Renamed legacy asset note: {os.path.basename(file_path)} -> {os.path.basename(target_file_path)}")
            file_path = target_file_path
        except Exception as e:
            sys.stderr.write(f"Warning: could not rename {file_path} to {target_file_path}: {e}\n")

    if not file_path:
        file_path = target_file_path

    if not os.path.exists(file_path):
        # Create new asset model
        if not asset_type:
            asset_type = determine_asset_type(name)
        issuer = determine_issuer(name) if asset_type == "etf" else None

        default_alloc = asset_allocation
        if default_alloc is None:
            if asset_type == "cash":
                default_alloc = {"cash": 100}
            elif asset_type in ("equity", "etf"):
                default_alloc = {"equity": 100}

        asset = Asset(
            ticker=ticker,
            name=name,
            platform=platform,
            portfolio=portfolio,
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            currency=currency,
            asset_type=asset_type,
            asset_allocation=default_alloc,
            issuer=issuer,
            isin=isin,
            yahoo_ticker=yahoo_ticker,
            stooq_ticker=stooq_ticker,
            tags=list(tags) if tags else [],
            last_updated=current_date,
            source=source,
        )
        if dominant_sector:
            asset.dominant_sector = dominant_sector
        if industry:
            asset.industry = industry
        if sector:
            asset.sector = sector
        if country:
            asset.country = country

        if template_fm:
            canonical_keys = set(Asset.model_fields.keys())
            for k, v in template_fm.items():
                if k not in canonical_keys and v is not None:
                    asset.extra_properties[k] = v

        enriched = _asset_enricher.enrich(asset)
        if portfolio:
            enriched.portfolio = portfolio
        elif not enriched.portfolio:
            enriched.portfolio = determine_portfolio(enriched.name, enriched.asset_type, enriched.dominant_sector)

        if dominant_sector:
            enriched.dominant_sector = dominant_sector
        if industry:
            enriched.industry = industry
        if sector:
            enriched.sector = sector
        if stooq_ticker:
            enriched.stooq_ticker = stooq_ticker
        if country:
            enriched.country = country

        if tags:
            for t in tags:
                if t not in enriched.tags:
                    enriched.tags.append(t)

        if asset_type == "cash":
            body = (
                f"\n# {name} ({ticker})\n\n"
                f"**Platform:** [[{platform}]]\n\n"
                f"## Investment Thesis / Notes\n"
                f"Information about reasoning for buying and keeping this asset.\n"
            )
        elif template_body:
            body = render_template_body(template_body, name, ticker, platform)
        else:
            body = (
                f"\n# {name} ({ticker})\n\n"
                f"**Platform:** [[{platform}]]\n\n"
                f"## 📈 Technical & Market Price Chart\n"
                f"```dataviewjs\n"
                f'await dv.view("99_System/Views/stooq_chart", {{\n'
                f"    ticker: dv.current().stooq_ticker,\n"
                f'    defaultRange: "1Y"\n'
                f"}});\n"
                f"```\n\n"
                f"## Investment Thesis / Notes\n"
                f"Information about reasoning for buying and keeping this asset.\n"
            )

        enriched.body = _inject_justetf_link(body, platform, enriched.justetf_url)
        enriched.body = _inject_issuer_link(enriched.body, platform, enriched.issuer_url)
        enriched.save(file_path)
        print(f"Created: {os.path.basename(file_path)}")
    else:
        # Update existing asset
        asset = Asset.from_file(file_path)
        if display_name and (
            not asset.name or asset.name.endswith("...") or asset.name.endswith("..") or asset.name == asset.ticker
        ):
            asset.name = display_name
        asset.platform = platform
        asset.quantity = quantity
        if avg_price is not None:
            asset.avg_price = avg_price
        asset.current_price = current_price
        asset.currency = currency or asset.currency
        asset.last_updated = current_date
        if isin and not asset.isin:
            asset.isin = isin
        if yahoo_ticker and not asset.yahoo_ticker:
            asset.yahoo_ticker = yahoo_ticker
        if stooq_ticker and not asset.stooq_ticker:
            asset.stooq_ticker = stooq_ticker
        if not asset.issuer and asset.asset_type == "etf":
            asset.issuer = determine_issuer(asset.name)
        if portfolio and not asset.portfolio:
            asset.portfolio = portfolio
        if asset_allocation and not asset.asset_allocation:
            asset.asset_allocation = asset_allocation
        if dominant_sector:
            asset.dominant_sector = dominant_sector
        if industry:
            asset.industry = industry
        if sector:
            asset.sector = sector
        if country:
            asset.country = country
        if tags:
            for t in tags:
                if t not in asset.tags:
                    asset.tags.append(t)
        asset.source = source
        if "source" in asset.extra_properties:
            del asset.extra_properties["source"]

        # Update body platform link if platform changed
        if asset.body:
            asset.body = re.sub(r"\*\*Platform:\*\* \[\[.*?\]\]", f"**Platform:** [[{platform}]]", asset.body)

        enriched = _asset_enricher.enrich(asset)
        if portfolio and not enriched.portfolio:
            enriched.portfolio = portfolio
        elif not enriched.portfolio:
            enriched.portfolio = determine_portfolio(enriched.name, enriched.asset_type, enriched.dominant_sector)

        if dominant_sector:
            enriched.dominant_sector = dominant_sector
        if industry:
            enriched.industry = industry
        if sector:
            enriched.sector = sector
        if stooq_ticker:
            enriched.stooq_ticker = stooq_ticker
        if country:
            enriched.country = country

        enriched.body = _inject_justetf_link(enriched.body, platform, enriched.justetf_url)
        enriched.body = _inject_issuer_link(enriched.body, platform, enriched.issuer_url)
        enriched.save(file_path)
        print(f"Updated: {os.path.basename(file_path)}")

    return file_path


def save_or_update_assets_parallel(
    asset_tasks: list[dict[str, Any]],
    max_workers: int | None = None,
    base_dir: str | None = None,
    show_progress: bool = True,
) -> tuple[set[str], set[str], int]:
    """Execute asset enrichment and saving concurrently using ThreadPoolExecutor.

    Parameters:
        asset_tasks: List of keyword-argument dicts for save_or_update_asset.
        max_workers: Optional number of worker threads. If omitted/None, automatically
                     detects the CPU hardware threads count (os.cpu_count()).
        base_dir: Optional base repository directory.
        show_progress: Whether to display a real-time Rich progress bar during enrichment.

    Returns:
        Tuple of (active_asset_paths: Set[str], active_tickers: Set[str], imported_count: int)
    """
    from platforms.common import get_max_workers

    if not asset_tasks:
        return set(), set(), 0

    workers = get_max_workers(max_workers, base_dir=base_dir)
    print(f"⚡ Processing {len(asset_tasks)} asset(s) concurrently across {workers} worker threads...")

    active_paths: set[str] = set()
    active_tickers: set[str] = set()
    imported_count = 0

    def _worker(task: dict[str, Any]) -> tuple[str, str, str | None]:
        fpath = save_or_update_asset(**task)
        ticker = task.get("ticker", "")
        isin = task.get("isin")
        return fpath, ticker, isin

    with create_progress(disable=not show_progress) as progress:
        task_id = progress.add_task(
            "[bold cyan]Enriching & saving assets[/bold cyan]",
            total=len(asset_tasks),
            status="Starting...",
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(_worker, task): task for task in asset_tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                label = task.get("ticker") or task.get("name") or "Asset"
                try:
                    fpath, ticker, isin = future.result()
                    active_paths.add(fpath)
                    if ticker:
                        active_tickers.add(ticker)
                    if isin:
                        active_tickers.add(isin)
                    imported_count += 1
                    progress.update(task_id, advance=1, status=f"[green]✓[/green] {label}")
                except Exception as e:
                    progress.update(task_id, advance=1, status=f"[red]✗[/red] {label}")
                    if hasattr(progress, "console") and progress.console:
                        progress.console.print(f"[red]Error processing asset {label}:[/red] {e}")
                    else:
                        sys.stderr.write(f"Error processing asset {label}: {e}\n")

        progress.update(task_id, status="[bold green]Completed[/bold green]")

    return active_paths, active_tickers, imported_count


def remove_missing_platform_assets(
    vault_assets_dir: str,
    platform: str,
    active_asset_paths: set[str],
    active_tickers: set[str] | None = None,
) -> list[str]:
    """Verify all existing platform assets in vault_assets_dir against active_asset_paths/active_tickers.

    Any existing asset whose platform matches (case-insensitive) and whose source is 'platform'
    (or not explicitly 'manual'), but is not present in active_asset_paths and active_tickers,
    will be removed from 10_Finance/Assets.

    Safety checks:
    - If active_asset_paths is empty, no deletions are performed to prevent accidental wipeouts
      caused by empty or unparseable export files.
    - Assets with source == 'manual' are protected and never removed.
    """
    if not active_asset_paths:
        print(
            f"Warning: No valid assets found in import for {platform}. Skipping removal of missing assets for safety."
        )
        return []

    normalized_active_paths = {os.path.normpath(os.path.abspath(p)) for p in active_asset_paths}
    removed_assets: list[str] = []

    if not os.path.exists(vault_assets_dir):
        return []

    target_plat = platform.strip().lower()

    for fname in sorted(os.listdir(vault_assets_dir)):
        if not fname.endswith(".md"):
            continue
        file_path = os.path.join(vault_assets_dir, fname)
        norm_path = os.path.normpath(os.path.abspath(file_path))
        if norm_path in normalized_active_paths:
            continue

        try:
            asset = Asset.from_file(file_path)
            asset_plat = (asset.platform or "").strip().lower()

            if asset_plat == target_plat:
                # Manual assets must never be removed by broker platform imports
                asset_source = (asset.source or "").strip().lower()
                if asset_source == "manual":
                    continue

                os.remove(file_path)
                removed_assets.append(fname)
                print(f"Removed missing platform asset: {fname} ({asset.name or asset.ticker})")
        except Exception as e:
            print(f"Warning: could not evaluate {fname} for removal: {e}")

    if removed_assets:
        print(f"Total removed {platform} assets missing from import: {len(removed_assets)}")
    return removed_assets
