import os
import sys
import glob
import argparse
import concurrent.futures
from datetime import datetime
from typing import Optional

# Ensure script directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from model.asset import Asset
from integrations.yfinance import calculate_value_pln, get_fx_rate_to_pln
from platforms.common import get_max_workers
from ui_progress import create_progress


def update_currencies(
    assets_dir: str,
    max_workers: Optional[int] = None,
    base_dir: Optional[str] = None,
    show_progress: bool = True,
    verbose: bool = False,
):
    """Update value_pln frontmatter field in all asset markdown files using live FX rates concurrently."""
    if not os.path.exists(assets_dir):
        print(f"Error: Assets directory not found at {assets_dir}")
        sys.exit(1)

    md_files = glob.glob(os.path.join(assets_dir, "*.md"))
    if not md_files:
        print(f"No markdown asset files found in {assets_dir}")
        return

    workers = get_max_workers(max_workers, base_dir=base_dir)
    current_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Updating currency values (value_pln) for assets in: {assets_dir}")
    print(f"⚡ Running concurrent currency update across {workers} worker threads...")
    print("-" * 75)

    def _process_file(file_path: str):
        filename = os.path.basename(file_path)
        try:
            asset = Asset.from_file(file_path)
            if not asset.ticker and not asset.name:
                return None, f"Skipping {filename} (no valid asset data)"

            currency = asset.currency or 'PLN'
            rate = get_fx_rate_to_pln(currency)
            val_pln = calculate_value_pln(asset.quantity, asset.current_price, currency)

            asset.value_pln = val_pln if val_pln is not None else 0.0
            asset.last_updated = current_date
            asset.save(file_path)

            val_str = f"{val_pln:,.2f} PLN" if val_pln is not None else "N/A"
            rate_str = "1.0" if currency.upper() == 'PLN' else f"{rate:.4f}"
            msg = f"Updated {filename:<25} | Currency: {currency:<4} | Rate: {rate_str:<7} | value_pln: {val_str}"
            return val_pln, msg
        except Exception as e:
            return None, f"Error updating {filename}: {e}"

    total_val_pln = 0.0
    updated_count = 0

    with create_progress(disable=not show_progress) as progress:
        task_id = progress.add_task(
            "[bold green]Updating live FX rates & PLN values[/bold green]",
            total=len(md_files),
            status="Starting...",
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_file, fpath): fpath for fpath in md_files}
            for future in concurrent.futures.as_completed(futures):
                fpath = futures[future]
                val_pln, msg = future.result()
                fname = os.path.basename(fpath)

                if val_pln is not None:
                    updated_count += 1
                    total_val_pln += val_pln
                    progress.update(task_id, advance=1, status=f"[green]✓[/green] {fname}")
                else:
                    progress.update(task_id, advance=1, status=f"[yellow]⚠[/yellow] {fname}")

                if verbose and hasattr(progress, "console") and progress.console:
                    progress.console.print(msg)
                elif not show_progress:
                    print(msg)

        progress.update(task_id, status="[bold green]Completed[/bold green]")

    print("-" * 75)
    print(f"Successfully updated {updated_count} asset files.")
    print(f"Total Portfolio Value: {total_val_pln:,.2f} PLN")


def main():
    parser = argparse.ArgumentParser(description="Update currency values (value_pln) for all assets.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of concurrent worker threads.")
    parser.add_argument("--assets-dir", dest="assets_dir", type=str, default=None, help="Path to assets directory.")
    parser.add_argument("--no-progress", dest="no_progress", action="store_true", default=False, help="Disable interactive rich progress bars.")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Print detailed update messages for every asset.")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(script_dir, "../.."))
    assets_dir = args.assets_dir or os.path.join(base_dir, "10_Finance", "Assets")
    update_currencies(
        assets_dir,
        max_workers=args.max_workers,
        base_dir=base_dir,
        show_progress=not args.no_progress,
        verbose=args.verbose,
    )


if __name__ == '__main__':
    main()
