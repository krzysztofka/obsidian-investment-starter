import csv
import os
import re
import sys
from datetime import datetime

# Ensure scripts directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from history.update_portfolio import update_portfolio_history

from platforms.base import BasePlatform, PlatformRegistry
from platforms.common import (
    clean_asset_display_name,
    determine_asset_type,
    load_template,
    parse_number,
    remove_missing_platform_assets,
    save_or_update_assets_parallel,
)


def find_degiro_csv(degiro_dir: str, custom_path: str | None = None, fallback_dir: str | None = None) -> str | None:
    """Finds target Degiro CSV file."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    candidate_dirs = [degiro_dir]
    if fallback_dir and os.path.exists(fallback_dir) and fallback_dir != degiro_dir:
        candidate_dirs.append(fallback_dir)

    for d in candidate_dirs:
        if not os.path.exists(d):
            continue
        default_csv = os.path.join(d, "degiro_current.csv")
        if os.path.exists(default_csv):
            return default_csv

        csv_files = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".csv")]
        if csv_files:

            def file_sort_key(filepath: str):
                m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(filepath))
                date_str = m.group(0) if m else ""
                return (date_str, os.path.getmtime(filepath))

            csv_files.sort(key=file_sort_key, reverse=True)
            return csv_files[0]

    return None


def import_degiro(
    csv_file_path: str | None = None,
    base_dir: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> int:
    """Import positions from Degiro CSV export into 10_Finance/Assets."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    degiro_dir = os.path.join(base_dir, "00_Raw", "degiro")
    legacy_dir = os.path.join(base_dir, "00_Raw", "Degiro")
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    csv_file = find_degiro_csv(degiro_dir, csv_file_path, fallback_dir=legacy_dir)
    if not csv_file or not os.path.exists(csv_file):
        print(f"Notice: No CSV file found in {degiro_dir}")
        return 0

    print(f"Importing positions from: {csv_file}")

    filename = os.path.basename(csv_file)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
    current_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

    template_fm, template_body = load_template(base_dir)

    asset_tasks = []
    with open(csv_file, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        prod_col = next((h for h in headers if h in ["Produkt", "Product", "Name"]), None)
        symbol_col = next((h for h in headers if h in ["Symbol/ISIN", "Symbol", "ISIN", "Ticker"]), None)
        qty_col = next((h for h in headers if h in ["Suma", "Quantity", "Aantal"]), None)
        price_col = next((h for h in headers if h in ["Kurs", "Price", "Koers"]), None)
        val_eur_col = next((h for h in headers if h in ["Wartość w EUR", "Value in EUR"]), None)

        currency_col = None
        for h in headers:
            if h in ["Lokalna wartość", "Currency", "Waluta"]:
                currency_col = h
                break

        for row in reader:
            name = (row.get(prod_col) or "").strip() if prod_col else ""
            if not name:
                continue

            ticker = (row.get(symbol_col) or "").strip() if symbol_col else ""
            quantity = parse_number(row.get(qty_col)) if qty_col else 0
            current_price = parse_number(row.get(price_col)) if price_col else 0
            currency = (row.get(currency_col) or "EUR").strip() if currency_col else "EUR"
            val_eur = parse_number(row.get(val_eur_col)) if val_eur_col else 0

            asset_type = determine_asset_type(name)
            if asset_type == "cash" or not ticker:
                if not ticker or ticker.startswith("CASH_"):
                    ticker = f"DEGIRO_CASH_{currency}"
                if quantity == 0 and (val_eur > 0 or current_price > 0):
                    quantity = val_eur if val_eur > 0 else current_price
                    current_price = 1.0
            else:
                if quantity <= 0:
                    continue

            isin = ticker if len(ticker) == 12 and ticker[:2].isalpha() else None
            name = clean_asset_display_name(name, isin=isin, ticker=ticker)

            asset_tasks.append(
                {
                    "vault_assets_dir": vault_assets_dir,
                    "platform": "Degiro",
                    "ticker": ticker,
                    "name": name,
                    "quantity": quantity,
                    "current_price": current_price,
                    "currency": currency,
                    "avg_price": None,
                    "isin": isin,
                    "current_date": current_date,
                    "template_fm": template_fm,
                    "template_body": template_body,
                    "source": "platform",
                }
            )

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    # Verify existing platform assets against new import file and remove missing
    remove_missing_platform_assets(
        vault_assets_dir=vault_assets_dir,
        platform="Degiro",
        active_asset_paths=active_asset_paths,
        active_tickers=active_tickers,
    )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


@PlatformRegistry.register
class DegiroPlatform(BasePlatform):
    """Degiro Broker Platform Extension."""

    id = "degiro"
    display_name = "Degiro"
    raw_folder = "degiro"
    default_mode = "csv"
    aliases = ["deg"]

    def can_handle_file(self, file_path: str) -> bool:
        norm = os.path.normpath(file_path).lower()
        return "degiro" in norm

    def run_import(
        self,
        file_path: str | None = None,
        use_api: bool | None = None,
        account_id: str | None = None,
        max_workers: int | None = None,
        show_progress: bool = True,
    ) -> int:
        return import_degiro(
            csv_file_path=file_path,
            base_dir=self.base_dir,
            max_workers=max_workers,
            show_progress=show_progress,
        )


if __name__ == "__main__":
    import_degiro()
