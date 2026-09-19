import os
import sys
import glob
from datetime import datetime

# Ensure script directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from model.asset import Asset
from integrations.yfinance import calculate_value_pln, get_fx_rate_to_pln


def update_currencies(assets_dir: str):
    """Update value_pln frontmatter field in all asset markdown files using live FX rates."""
    if not os.path.exists(assets_dir):
        print(f"Error: Assets directory not found at {assets_dir}")
        sys.exit(1)

    md_files = glob.glob(os.path.join(assets_dir, "*.md"))
    if not md_files:
        print(f"No markdown asset files found in {assets_dir}")
        return

    current_date = datetime.now().strftime("%Y-%m-%d")
    total_val_pln = 0.0
    updated_count = 0

    print(f"Updating currency values (value_pln) for assets in: {assets_dir}")
    print("-" * 75)

    for file_path in md_files:
        filename = os.path.basename(file_path)
        asset = Asset.from_file(file_path)
        if not asset.ticker and not asset.name:
            print(f"Skipping {filename} (no valid asset data)")
            continue

        currency = asset.currency or 'PLN'
        rate = get_fx_rate_to_pln(currency)
        val_pln = calculate_value_pln(asset.quantity, asset.current_price, currency)

        asset.value_pln = val_pln if val_pln is not None else 0.0
        asset.last_updated = current_date
        asset.save(file_path)

        updated_count += 1
        val_str = f"{val_pln:,.2f} PLN" if val_pln is not None else "N/A"
        rate_str = "1.0" if currency.upper() == 'PLN' else f"{rate:.4f}"
        print(f"Updated {filename:<25} | Currency: {currency:<4} | Rate: {rate_str:<7} | value_pln: {val_str}")

        if val_pln is not None:
            total_val_pln += val_pln

    print("-" * 75)
    print(f"Successfully updated {updated_count} asset files.")
    print(f"Total Portfolio Value: {total_val_pln:,.2f} PLN")


def main():
    base_dir = os.path.abspath(os.path.join(script_dir, "../.."))
    assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    update_currencies(assets_dir)


if __name__ == '__main__':
    main()
