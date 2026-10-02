import os
import sys
import csv
import re
from datetime import datetime
from typing import Optional, List, Dict, Set

# Ensure scripts directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from platforms.common import (
    parse_number,
    load_template,
    save_or_update_asset,
    save_or_update_assets_parallel,
    remove_missing_platform_assets,
    load_import_config,
    clean_asset_display_name,
    KNOWN_ETF_NAMES,
)
from history.update_portfolio import update_portfolio_history


def find_exante_csv(base_dir: str, custom_path: Optional[str] = None) -> Optional[str]:
    """Return the most recent Exante CSV file path."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]

    exante_dir = os.path.join(base_dir, "00_Raw", "Exante")
    if not os.path.exists(exante_dir):
        return None
    candidates = [os.path.join(exante_dir, f) for f in os.listdir(exante_dir) if f.lower().endswith('.csv')]
    if not candidates:
        return None

    def file_sort_key(filepath: str):
        m = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filepath))
        date_str = m.group(0) if m else ''
        return (date_str, os.path.getmtime(filepath))

    candidates.sort(key=file_sort_key, reverse=True)
    return candidates[0]


def find_section(lines: List[str], *keywords: str) -> List[Dict[str, str]]:
    """Find a section by matching all keywords (case-insensitive) in the title line.

    The Exante CSV is structured as consecutive sections separated by blank lines.
    Each section starts with a title line (no tabs), followed by a header line with
    column names, then data rows.
    """
    keywords_lower = [kw.lower() for kw in keywords]

    title_idx = None
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if all(kw in line_lower for kw in keywords_lower):
            title_idx = i
            break

    if title_idx is None:
        return []

    header_idx = title_idx + 1
    while header_idx < len(lines) and not lines[header_idx].strip():
        header_idx += 1
    if header_idx >= len(lines):
        return []

    section_end = len(lines)
    for j in range(header_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped or '\t' not in lines[j]:
            section_end = j
            break

    return list(csv.DictReader(lines[header_idx:section_end], delimiter='\t'))


def import_exante_api(
    account_id: Optional[str] = None,
    base_dir: Optional[str] = None,
    client: Optional[Any] = None,
    max_workers: Optional[int] = None,
    show_progress: bool = True,
) -> int:
    """Import positions and cash balances directly from Exante REST API into 10_Finance/Assets."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    from integrations.exante.service import get_exante_client

    cli = client or get_exante_client(account_id=account_id)
    if not cli:
        print("Error: Exante API is not configured. Please set EXANTE_API_KEY and EXANTE_API_SECRET in .env.")
        return 0

    print("Fetching live portfolio data from Exante API...")
    try:
        portfolio_data = cli.fetch_portfolio(account_id=account_id)
    except Exception as e:
        print(f"Error fetching data from Exante API: {e}")
        return 0

    if not portfolio_data:
        print("Error: No data returned from Exante API.")
        return 0

    current_date = portfolio_data.get("session_date") or datetime.now().strftime("%Y-%m-%d")
    template_fm, template_body = load_template(base_dir)

    asset_tasks = []

    # 1. Process cash balances
    for cash in portfolio_data.get("cash_balances", []):
        currency_code = cash.get("iso") or cash.get("currency") or "EUR"
        instrument = cash.get("instrument") or f"{currency_code} Cash Balance"
        value = cash.get("value", 0.0)
        ticker = f"EXANTE_CASH_{currency_code}"

        asset_tasks.append({
            "vault_assets_dir": vault_assets_dir,
            "platform": "Exante",
            "ticker": ticker,
            "name": instrument,
            "quantity": value,
            "current_price": 1.0,
            "currency": currency_code,
            "avg_price": None,
            "isin": None,
            "current_date": current_date,
            "template_fm": template_fm,
            "template_body": template_body,
            "source": "platform",
        })

    # 2. Process stocks & ETFs positions
    for pos in portfolio_data.get("positions", []):
        ticker = pos.get("ticker") or pos.get("instrument")
        name = pos.get("name") or ticker
        quantity = pos.get("quantity", 0.0)
        avg_price = pos.get("avg_price")
        current_price = pos.get("current_price", 0.0)
        currency = pos.get("currency") or "EUR"
        isin = pos.get("isin")

        if not ticker or quantity <= 0:
            continue

        name = clean_asset_display_name(name, isin=isin, ticker=ticker)

        asset_tasks.append({
            "vault_assets_dir": vault_assets_dir,
            "platform": "Exante",
            "ticker": ticker,
            "name": name,
            "quantity": quantity,
            "current_price": current_price,
            "currency": currency,
            "avg_price": avg_price,
            "isin": isin,
            "current_date": current_date,
            "template_fm": template_fm,
            "template_body": template_body,
            "source": "platform",
        })

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    # 3. Verify existing platform assets against new import and remove missing
    remove_missing_platform_assets(
        vault_assets_dir=vault_assets_dir,
        platform="Exante",
        active_asset_paths=active_asset_paths,
        active_tickers=active_tickers,
    )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


def import_exante(
    csv_file_path: Optional[str] = None,
    base_dir: Optional[str] = None,
    use_api: Optional[bool] = None,
    account_id: Optional[str] = None,
    max_workers: Optional[int] = None,
    show_progress: bool = True,
) -> int:
    """Import positions from Exante CSV export or Exante REST API into 10_Finance/Assets."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    # Resolve default import mode if not explicitly provided
    if use_api is None:
        if csv_file_path:
            use_api = False
        else:
            cfg = load_import_config(base_dir)
            use_api = cfg.get("exante", {}).get("default_mode", "api").lower() == "api"

    if use_api:
        return import_exante_api(account_id=account_id, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)

    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    csv_file = find_exante_csv(base_dir, csv_file_path)
    if not csv_file or not os.path.exists(csv_file):
        print(f"Error: No Exante CSV file found in {base_dir}")
        return 0

    print(f"Importing Exante positions from: {csv_file}")

    filename = os.path.basename(csv_file)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
    current_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

    template_fm, template_body = load_template(base_dir)

    with open(csv_file, mode='r', encoding='utf-16') as f:
        lines = [ln.rstrip('\r') for ln in f]

    asset_tasks = []

    # 1. Process cash balance section
    cash_rows = find_section(lines, 'cash', 'balance')
    for row in cash_rows:
        instrument = (row.get('Instrument') or '').strip()
        iso = (row.get('ISO') or '').strip()
        value = parse_number(row.get('Value'))
        if not instrument:
            continue

        currency_code = iso or 'EUR'
        ticker = f"EXANTE_CASH_{currency_code}"

        asset_tasks.append({
            "vault_assets_dir": vault_assets_dir,
            "platform": 'Exante',
            "ticker": ticker,
            "name": instrument,
            "quantity": value,
            "current_price": 1.0,
            "currency": currency_code,
            "avg_price": None,
            "isin": None,
            "current_date": current_date,
            "template_fm": template_fm,
            "template_body": template_body,
            "source": 'platform',
        })

    # 2. Process stocks & ETFs section
    stock_rows = find_section(lines, 'stocks', 'etfs')
    for row in stock_rows:
        instrument = (row.get('Instrument') or '').strip()
        name = (row.get('Name') or '').strip()
        quantity = parse_number(row.get('QTY'))
        avg_price = parse_number(row.get('Avg Price'))
        current_price = parse_number(row.get('Price'))
        currency = (row.get('Currency') or 'EUR').strip()
        isin = (row.get('ISIN') or '').strip()
        if not instrument:
            continue
        if quantity <= 0:
            continue

        name = clean_asset_display_name(name, isin=isin, ticker=instrument)

        asset_tasks.append({
            "vault_assets_dir": vault_assets_dir,
            "platform": 'Exante',
            "ticker": instrument,
            "name": name,
            "quantity": quantity,
            "current_price": current_price,
            "currency": currency,
            "avg_price": avg_price,
            "isin": isin,
            "current_date": current_date,
            "template_fm": template_fm,
            "template_body": template_body,
            "source": 'platform',
        })

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    # 3. Verify existing platform assets against new import file and remove missing
    remove_missing_platform_assets(
        vault_assets_dir=vault_assets_dir,
        platform='Exante',
        active_asset_paths=active_asset_paths,
        active_tickers=active_tickers,
    )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Import assets from Exante CSV or REST API.")
    parser.add_argument("-f", "--file", dest="file", type=str, default=None, help="Path to Exante CSV file.")
    parser.add_argument("--api", dest="api", action="store_true", default=None, help="Fetch portfolio from Exante REST API.")
    parser.add_argument("--csv", dest="csv", action="store_true", default=False, help="Force CSV import mode.")
    parser.add_argument("--account", dest="account_id", type=str, default=None, help="Exante account ID.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of worker threads.")
    parser.add_argument("positional_file", nargs="?", default=None, help="Optional Exante CSV file path.")

    args = parser.parse_args()
    target_file = args.file or args.positional_file
    use_api = False if args.csv else (True if args.api else None)
    import_exante(csv_file_path=target_file, use_api=use_api, account_id=args.account_id, max_workers=args.max_workers)

