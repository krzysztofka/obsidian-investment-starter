import os
import sys
import re
import fnmatch
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple, Any, Union

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
)
from history.update_portfolio import update_portfolio_history


def format_maturity_date_yyyymmdd(maturity_str: Optional[str]) -> Optional[str]:
    """Format maturity date into YYYYMMDD string format."""
    if not maturity_str:
        return None
    s = str(maturity_str).strip()
    # YYYY-MM-DD or YYYY.MM.DD or YYYY/MM/DD
    m = re.match(r'^(\d{4})[^\d]?(\d{2})[^\d]?(\d{2})$', s)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    # DD.MM.YYYY or DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r'^(\d{2})[^\d](\d{2})[^\d](\d{4})$', s)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    digits = re.sub(r'\D', '', s)
    if len(digits) == 8:
        return digits
    return None


def load_pkobp_config(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load PKOBP configuration rules from config.yaml."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    candidate_paths = [
        os.path.join(base_dir, "config.yaml"),
        os.path.join(base_dir, "99_System", "config.yaml"),
    ]

    import yaml
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if isinstance(cfg, dict) and "import" in cfg:
                    imp_cfg = cfg["import"]
                    if isinstance(imp_cfg, dict) and "pkobp" in imp_cfg:
                        return imp_cfg["pkobp"]
            except Exception:
                pass

    return {
        "default_mode": "xls",
        "default_portfolio": "Long term",
        "rules": [
            {"ticker": "EDO0936", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "ROD", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "ROK", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "OTS", "portfolio": "Safety net"},
            {"prefix": "ROR", "portfolio": "Safety net"},
        ]
    }


def find_pkobp_file(pkobp_dir: str, custom_path: Optional[str] = None) -> Optional[str]:
    """Find target PKO BP export file (.xls or .xlsx)."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]

    if not os.path.exists(pkobp_dir):
        return None

    files = [
        os.path.join(pkobp_dir, f)
        for f in os.listdir(pkobp_dir)
        if f.lower().endswith(('.xls', '.xlsx')) and not f.startswith('~')
    ]
    if not files:
        return None

    def file_sort_key(filepath: str):
        m = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filepath))
        date_str = m.group(0) if m else ''
        return (date_str, os.path.getmtime(filepath))

    files.sort(key=file_sort_key, reverse=True)
    return files[0]


def parse_pkobp_sheet(file_path: str) -> List[Dict[str, Any]]:
    """Parse positions from PKO BP register status Excel file."""
    import xlrd

    wb = xlrd.open_workbook(file_path)
    sheet = wb.sheet_by_index(0)

    if sheet.nrows < 2:
        return []

    # Find header row
    header_row_idx = -1
    for r in range(min(10, sheet.nrows)):
        row_vals = [str(sheet.cell_value(r, c)).strip().upper() for c in range(sheet.ncols)]
        if any('EMISJA' in v for v in row_vals):
            header_row_idx = r
            break

    if header_row_idx == -1:
        raise ValueError(f"Could not find valid header row with 'EMISJA' column in {file_path}")

    headers = [str(sheet.cell_value(header_row_idx, c)).strip().upper() for c in range(sheet.ncols)]

    def find_col(possible_names: List[str]) -> Optional[int]:
        for idx, h in enumerate(headers):
            for name in possible_names:
                if name.upper() in h:
                    return idx
        return None

    col_emission = find_col(['EMISJA'])
    col_qty_avail = find_col(['DOSTĘPNA LICZBA', 'DOSTEPNA LICZBA', 'LICZBA OBLIGACJI', 'ILOŚĆ', 'ILOSC'])
    col_qty_blocked = find_col(['ZABLOKOWANA LICZBA'])
    col_nom_val = find_col(['WARTOŚĆ NOMINALNA', 'WARTOSC NOMINALNA', 'NOMINAŁ', 'NOMINAL'])
    col_curr_val = find_col(['WARTOŚĆ AKTUALNA', 'WARTOSC AKTUALNA', 'WARTOŚĆ RYNKOWA', 'WARTOSC'])
    col_maturity = find_col(['DATA WYKUPU', 'WYKUP', 'TERMIN WYKUPU'])

    rows: List[Dict[str, Any]] = []
    for r in range(header_row_idx + 1, sheet.nrows):
        emission = str(sheet.cell_value(r, col_emission)).strip() if col_emission is not None else ''
        if not emission or emission.upper().startswith('SUMA') or emission.upper().startswith('RAZEM'):
            continue

        qty_avail = parse_number(sheet.cell_value(r, col_qty_avail)) if col_qty_avail is not None else 0
        qty_blocked = parse_number(sheet.cell_value(r, col_qty_blocked)) if col_qty_blocked is not None else 0
        total_qty = qty_avail + qty_blocked

        if total_qty <= 0:
            continue

        nom_val = parse_number(sheet.cell_value(r, col_nom_val)) if col_nom_val is not None else 0
        curr_val = parse_number(sheet.cell_value(r, col_curr_val)) if col_curr_val is not None else 0

        maturity_val = sheet.cell_value(r, col_maturity) if col_maturity is not None else ''
        if isinstance(maturity_val, float):
            # Excel date serial
            try:
                date_tuple = xlrd.xldate_as_tuple(maturity_val, wb.datemode)
                maturity_str = f"{date_tuple[0]:04d}-{date_tuple[1]:02d}-{date_tuple[2]:02d}"
            except Exception:
                maturity_str = str(maturity_val)
        else:
            maturity_str = str(maturity_val).strip()

        rows.append({
            'emission': emission,
            'quantity': total_qty,
            'nominal_value': nom_val if nom_val > 0 else total_qty * 100.0,
            'current_value': curr_val if curr_val > 0 else (nom_val if nom_val > 0 else total_qty * 100.0),
            'maturity_date': maturity_str,
        })

    return rows


def resolve_portfolio_allocation(
    emission: str,
    total_qty: Union[int, float],
    nominal_val: Union[int, float],
    current_val: Union[int, float],
    config: Dict[str, Any],
    maturity_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Determine how many units/amount of an emission go into which portfolio based on config rules.

    Returns a list of dicts, each representing a position slice:
      [{'ticker': '...', 'name': '...', 'portfolio': '...', 'quantity': ..., 'current_price': ..., 'value_pln': ...}]
    """
    default_portfolio = config.get('default_portfolio', 'Long term')
    rules = config.get('rules', [])

    price_per_unit = (current_val / total_qty) if total_qty > 0 else 100.0
    nominal_price_per_unit = (nominal_val / total_qty) if total_qty > 0 else 100.0

    maturity_compact = format_maturity_date_yyyymmdd(maturity_date)
    ticker_base = f"{emission}_{maturity_compact}" if maturity_compact else emission

    matched_rule = None
    emission_upper = emission.strip().upper()
    ticker_base_upper = ticker_base.strip().upper()

    for rule in rules:
        r_ticker = rule.get('ticker')
        if r_ticker and (r_ticker.strip().upper() == emission_upper or r_ticker.strip().upper() == ticker_base_upper):
            matched_rule = rule
            break

        r_prefix = rule.get('prefix')
        if r_prefix and (emission_upper.startswith(r_prefix.strip().upper()) or ticker_base_upper.startswith(r_prefix.strip().upper())):
            matched_rule = rule
            break

        r_series = rule.get('series')
        if r_series and (fnmatch.fnmatch(emission_upper, r_series.strip().upper()) or fnmatch.fnmatch(ticker_base_upper, r_series.strip().upper()) or r_series.strip().upper() in emission_upper):
            matched_rule = rule
            break

    if not matched_rule:
        # Default allocation: entire position to default_portfolio
        return [{
            'ticker': ticker_base,
            'name': ticker_base,
            'portfolio': default_portfolio,
            'quantity': total_qty,
            'current_price': round(price_per_unit, 2),
            'value_pln': round(current_val, 2),
        }]

    target_portfolio = matched_rule.get('portfolio', default_portfolio)
    overflow_portfolio = matched_rule.get('overflow_portfolio', default_portfolio)

    max_amount = matched_rule.get('max_amount')
    max_qty = matched_rule.get('max_quantity')

    rule_qty_limit = None
    if max_qty is not None:
        rule_qty_limit = parse_number(max_qty)
    elif max_amount is not None:
        amount_limit = parse_number(max_amount)
        rule_qty_limit = amount_limit / nominal_price_per_unit

    if rule_qty_limit is None or total_qty <= rule_qty_limit:
        # Entire position fits in the rule portfolio
        return [{
            'ticker': ticker_base,
            'name': ticker_base,
            'portfolio': target_portfolio,
            'quantity': total_qty,
            'current_price': round(price_per_unit, 2),
            'value_pln': round(current_val, 2),
        }]

    # Position is split between target_portfolio and overflow_portfolio
    rule_qty = int(rule_qty_limit) if float(rule_qty_limit).is_integer() else rule_qty_limit
    overflow_qty = total_qty - rule_qty

    rule_val = round(rule_qty * price_per_unit, 2)
    overflow_val = round(overflow_qty * price_per_unit, 2)

    safe_target = target_portfolio.replace(' ', '_')
    safe_overflow = overflow_portfolio.replace(' ', '_')

    return [
        {
            'ticker': f"{ticker_base}_{safe_target}",
            'name': f"{ticker_base} ({target_portfolio})",
            'portfolio': target_portfolio,
            'quantity': rule_qty,
            'current_price': round(price_per_unit, 2),
            'value_pln': rule_val,
        },
        {
            'ticker': f"{ticker_base}_{safe_overflow}",
            'name': f"{ticker_base} ({overflow_portfolio})",
            'portfolio': overflow_portfolio,
            'quantity': overflow_qty,
            'current_price': round(price_per_unit, 2),
            'value_pln': overflow_val,
        }
    ]


def import_pkobp(
    file_path: Optional[str] = None,
    base_dir: Optional[str] = None,
    csv_file_path: Optional[str] = None,
    max_workers: Optional[int] = None,
    show_progress: bool = True,
) -> int:
    """Import positions from PKO BP register status Excel export into 10_Finance/Assets."""
    if file_path is None and csv_file_path is not None:
        file_path = csv_file_path
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    pkobp_dir = os.path.join(base_dir, "00_Raw", "pkobp")
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    excel_file = find_pkobp_file(pkobp_dir, file_path)
    if not excel_file or not os.path.exists(excel_file):
        print(f"Error: No valid Excel file found in {pkobp_dir}")
        return 0

    print(f"Importing PKO BP treasury bonds from: {excel_file}")

    filename = os.path.basename(excel_file)
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', filename)
    current_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

    config = load_pkobp_config(base_dir)
    raw_positions = parse_pkobp_sheet(excel_file)

    if not raw_positions:
        print("Warning: No positions found in PKO BP export.")
        return 0

    template_fm, template_body = load_template(base_dir)

    asset_tasks = []

    for pos in raw_positions:
        emission = pos['emission']
        total_qty = pos['quantity']
        nom_val = pos['nominal_value']
        curr_val = pos['current_value']
        maturity = pos.get('maturity_date', '')

        slices = resolve_portfolio_allocation(
            emission=emission,
            total_qty=total_qty,
            nominal_val=nom_val,
            current_val=curr_val,
            config=config,
            maturity_date=maturity,
        )

        for sl in slices:
            ticker = sl['ticker']
            name = sl['name']
            portfolio = sl['portfolio']
            qty = sl['quantity']
            cur_price = sl['current_price']

            # Build custom bond markdown body
            bond_body = (
                f"\n# Polish government bonds ({name})\n\n"
                f"**Platform:** [[PKOBP]]\n"
            )
            if maturity:
                bond_body += f"**Maturity Date:** {maturity}\n"

            bond_body += (
                f"\n## 📈 Technical & Market Price Chart\n"
                f"```dataviewjs\n"
                f'await dv.view("99_System/Views/stooq_chart", {{\n'
                f"    ticker: dv.current().stooq_ticker,\n"
                f'    defaultRange: "1Y"\n'
                f"}});\n"
                f"```\n\n"
                f"## Investment Thesis / Notes\n"
                f"Polish retail treasury bond {emission} (Maturity: {maturity or 'N/A'}).\n"
            )

            asset_tasks.append({
                "vault_assets_dir": vault_assets_dir,
                "platform": 'PKOBP',
                "ticker": ticker,
                "name": name,
                "quantity": qty,
                "current_price": cur_price,
                "currency": 'PLN',
                "avg_price": 100.0,
                "isin": None,
                "current_date": current_date,
                "template_fm": template_fm,
                "template_body": bond_body,
                "source": 'platform',
                "portfolio": portfolio,
                "asset_type": 'bond',
                "asset_allocation": {'bonds': 100},
                "dominant_sector": "Sovereign",
                "industry": "Sovereign",
                "sector": "Sovereign",
                "stooq_ticker": "10ply.b",
                "country": "Poland",
            })

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    # Prune obsolete PKOBP platform assets missing from import
    remove_missing_platform_assets(
        vault_assets_dir=vault_assets_dir,
        platform='PKOBP',
        active_asset_paths=active_asset_paths,
        active_tickers=active_tickers,
    )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Import PKO BP treasury retail bonds.")
    parser.add_argument("-f", "--file", dest="file", type=str, default=None, help="Path to PKO BP Excel file.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of worker threads.")
    parser.add_argument("positional_file", nargs="?", default=None, help="Optional PKO BP Excel file path.")

    args = parser.parse_args()
    target_file = args.file or args.positional_file
    import_pkobp(file_path=target_file, max_workers=args.max_workers)
