import os
import sys
import re
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple, Any

# Ensure scripts directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from platforms.common import (
    parse_number,
    determine_asset_type,
    load_template,
    save_or_update_asset,
    remove_missing_platform_assets,
    ensure_utf8_file,
)
from history.update_portfolio import update_portfolio_history


# Mapping for popular UCITS ETFs traded via XETRA / European exchanges to known ISINs and Yahoo tickers
KNOWN_ETF_MAPPING: Dict[str, Dict[str, Any]] = {
    'V80A': {
        'isin': 'IE00BMVB5R75',
        'yahoo_ticker': 'V80A.DE',
        'name': 'Vanguard LifeStrategy 80% Equity UCITS ETF',
        'allocation': {'equity': 80, 'bonds': 20, 'cash': 0},
    },
    'VNGA80': {
        'isin': 'IE00BMVB5R75',
        'yahoo_ticker': 'V80A.DE',
        'name': 'Vanguard LifeStrategy 80% Equity UCITS ETF',
        'allocation': {'equity': 80, 'bonds': 20, 'cash': 0},
    },
    'V60A': {
        'isin': 'IE00BMVB5P51',
        'yahoo_ticker': 'V60A.DE',
        'name': 'Vanguard LifeStrategy 60% Equity UCITS ETF',
        'allocation': {'equity': 60, 'bonds': 40, 'cash': 0},
    },
    'VNGA60': {
        'isin': 'IE00BMVB5P51',
        'yahoo_ticker': 'V60A.DE',
        'name': 'Vanguard LifeStrategy 60% Equity UCITS ETF',
        'allocation': {'equity': 60, 'bonds': 40, 'cash': 0},
    },
    'V40A': {
        'isin': 'IE00BMVB5M21',
        'yahoo_ticker': 'V40A.DE',
        'name': 'Vanguard LifeStrategy 40% Equity UCITS ETF',
        'allocation': {'equity': 40, 'bonds': 60, 'cash': 0},
    },
    'VNGA40': {
        'isin': 'IE00BMVB5M21',
        'yahoo_ticker': 'V40A.DE',
        'name': 'Vanguard LifeStrategy 40% Equity UCITS ETF',
        'allocation': {'equity': 40, 'bonds': 60, 'cash': 0},
    },
    'V20A': {
        'isin': 'IE00BMVB5K07',
        'yahoo_ticker': 'V20A.DE',
        'name': 'Vanguard LifeStrategy 20% Equity UCITS ETF',
        'allocation': {'equity': 20, 'bonds': 80, 'cash': 0},
    },
    'VNGA20': {
        'isin': 'IE00BMVB5K07',
        'yahoo_ticker': 'V20A.DE',
        'name': 'Vanguard LifeStrategy 20% Equity UCITS ETF',
        'allocation': {'equity': 20, 'bonds': 80, 'cash': 0},
    },
    'VWCE': {
        'isin': 'IE00BK5BQT80',
        'yahoo_ticker': 'VWCE.DE',
        'name': 'Vanguard FTSE All-World UCITS ETF (USD) Accumulating',
    },
    'VWRL': {
        'isin': 'IE00B3RBWM25',
        'yahoo_ticker': 'VWRL.DE',
        'name': 'Vanguard FTSE All-World UCITS ETF (USD) Distributing',
    },
    'SPPW': {
        'isin': 'IE00BFY0GT14',
        'yahoo_ticker': 'SPPW.DE',
        'name': 'SPDR MSCI World UCITS ETF',
    },
    'SXR8': {
        'isin': 'IE00B5BMR087',
        'yahoo_ticker': 'SXR8.DE',
        'name': 'iShares Core S&P 500 UCITS ETF (Acc)',
    },
    'EUNL': {
        'isin': 'IE00B4L5Y983',
        'yahoo_ticker': 'EUNL.DE',
        'name': 'iShares Core MSCI World UCITS ETF (Acc)',
    },
    'IS3N': {
        'isin': 'IE00BKM4GZ66',
        'yahoo_ticker': 'IS3N.DE',
        'name': 'iShares Core MSCI Emerging Markets IMI UCITS ETF (Acc)',
    },
    'QDVE': {
        'isin': 'IE00B3WJKG14',
        'yahoo_ticker': 'QDVE.DE',
        'name': 'iShares S&P 500 Information Technology Sector UCITS ETF',
    },
    'SXRV': {
        'isin': 'IE00B53SZB19',
        'yahoo_ticker': 'SXRV.DE',
        'name': 'iShares NASDAQ 100 UCITS ETF (Acc)',
    },
    'DBX0AN': {
        'isin': 'LU0290358497',
        'yahoo_ticker': 'DBX0AN.DE',
        'name': 'Xtrackers II EUR Overnight Rate Swap UCITS ETF',
    },
    'XEON': {
        'isin': 'LU0290358497',
        'yahoo_ticker': 'XEON.DE',
        'name': 'Xtrackers II EUR Overnight Rate Swap UCITS ETF',
    },
}

EXCHANGE_SUFFIX_MAP = {
    'DEU-XETRA': '.DE',
    'DEU-FRA': '.F',
    'GPW-AKCJE': '.WA',
    'GPW-ETF': '.WA',
    'GPW': '.WA',
    'WSE': '.WA',
    'USA-NASDAQ': '',
    'USA-NYSE': '',
    'USA': '',
    'LSE': '.L',
    'EURONEXT-AMS': '.AS',
    'EURONEXT-PAR': '.PA',
}


def detect_account_type_from_path(file_path: str) -> str:
    """Detect whether file corresponds to IKE or IKZE based on path and file name."""
    norm = file_path.lower()
    if 'ikze' in norm:
        return 'ikze'
    if 'ike' in norm:
        return 'ike'
    return 'ikze'


def find_mbm_csv(
    mbm_dir: str,
    account_type: Optional[str] = None,
    custom_path: Optional[str] = None
) -> Optional[str]:
    """Find the most recent mBM CSV file for a given account type ('ike' or 'ikze')."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    if not os.path.exists(mbm_dir):
        return None

    target_type = (account_type or 'ikze').lower()
    candidates: List[str] = []

    for f in os.listdir(mbm_dir):
        if not f.lower().endswith('.csv'):
            continue
        full_path = os.path.join(mbm_dir, f)
        fname_lower = f.lower()

        if target_type == 'ikze':
            if 'ikze' in fname_lower:
                candidates.append(full_path)
        elif target_type == 'ike':
            if 'ike' in fname_lower and 'ikze' not in fname_lower:
                candidates.append(full_path)
        else:
            candidates.append(full_path)

    if not candidates:
        return None

    def file_sort_key(filepath: str):
        m = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(filepath))
        date_str = m.group(0) if m else ''
        return (date_str, os.path.getmtime(filepath))

    candidates.sort(key=file_sort_key, reverse=True)
    return candidates[0]


def parse_mbm_file_content(file_path: str) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
    """Read mBM CSV file, ensure UTF-8 encoding (converting in-place if legacy cp1250),
    and extract metadata and rows of assets.

    Returns:
        (file_date, account_number, rows)
    """
    raw_content = ensure_utf8_file(file_path)
    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]

    file_date = None
    account_number = None

    # Check for date in metadata lines
    for i, line in enumerate(lines):
        if line.startswith('#Data') and i + 1 < len(lines):
            d_val = lines[i + 1].strip()
            # Parse DD.MM.YYYY
            d_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', d_val)
            if d_match:
                file_date = f"{d_match.group(3)}-{d_match.group(2)}-{d_match.group(1)}"
        elif line.startswith('#Nr rachunku') and i + 1 < len(lines):
            account_number = lines[i + 1].strip()

    # Fallback date from filename
    if not file_date:
        fn_match = re.search(r'\d{4}-\d{2}-\d{2}', os.path.basename(file_path))
        if fn_match:
            file_date = fn_match.group(0)

    # Locate table header
    header_idx = None
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if 'papier' in line_lower and ('giełda' in line_lower or 'gielda' in line_lower or 'kurs' in line_lower):
            header_idx = i
            break

    if header_idx is None:
        return file_date, account_number, []

    headers = [h.strip() for h in lines[header_idx].split(';')]
    col_paper = next((i for i, h in enumerate(headers) if h.lower() in ['papier', 'instrument', 'nazwa']), None)
    col_exchange = next((i for i, h in enumerate(headers) if h.lower() in ['giełda', 'gielda', 'rynek']), None)
    col_qty = next((i for i, h in enumerate(headers) if any(k in h.lower() for k in ['liczba', 'ilość', 'ilosc', 'suma', 'quantity'])), None)
    col_price = next((i for i, h in enumerate(headers) if h.lower() in ['kurs', 'cena', 'price']), None)

    # Find currency columns (first is price currency, second is total value currency)
    currency_indices = [i for i, h in enumerate(headers) if h.lower() in ['waluta', 'currency']]
    col_curr = currency_indices[0] if currency_indices else None

    parsed_rows: List[Dict[str, Any]] = []

    for line in lines[header_idx + 1:]:
        if not line or ';' not in line:
            continue
        parts = [p.strip() for p in line.split(';')]
        if len(parts) <= max(filter(lambda x: x is not None, [col_paper, col_qty, col_price])):
            continue

        raw_paper = parts[col_paper] if col_paper is not None else ''
        if not raw_paper:
            continue

        # Check for summary row footer
        if any(term in raw_paper.lower() for term in ['łączna wycena', 'laczna wycena', 'suma', 'razem', 'podsumowanie']):
            break

        exchange = parts[col_exchange] if col_exchange is not None and col_exchange < len(parts) else ''
        raw_qty = parts[col_qty] if col_qty is not None and col_qty < len(parts) else '0'
        raw_price = parts[col_price] if col_price is not None and col_price < len(parts) else '0'
        currency = parts[col_curr] if col_curr is not None and col_curr < len(parts) else 'PLN'

        # Parse quantity handling blocks like '85 (0)' or '85'
        qty_match = re.match(r'([\d\s,.]+)(?:\s*\(([\d\s,.]+)\))?', raw_qty)
        if qty_match:
            avail = parse_number(qty_match.group(1))
            blocked = parse_number(qty_match.group(2)) if qty_match.group(2) else 0
            quantity = avail + blocked
        else:
            quantity = parse_number(raw_qty)

        price = parse_number(raw_price)

        if quantity <= 0:
            continue

        parsed_rows.append({
            'raw_paper': raw_paper,
            'exchange': exchange,
            'quantity': quantity,
            'price': price,
            'currency': currency,
        })

    return file_date, account_number, parsed_rows


def resolve_instrument_identifiers(raw_paper: str, exchange: str, account_type: str) -> Dict[str, Any]:
    """Resolve base ticker, vault ticker, yahoo ticker, ISIN, name, and asset properties."""
    clean_paper = raw_paper.strip()
    account_upper = account_type.upper()

    tokens = clean_paper.split()
    first_token = tokens[0] if tokens else clean_paper

    # Clean ticker symbols like 'V80A GR ETF' -> 'V80A'
    base_symbol = first_token
    for suffix in ['GR', 'GY', 'LN', 'US', 'FP', 'NA', 'SW', 'PW', 'ETF', 'UCITS', 'ETC', 'ETN']:
        if len(tokens) > 1 and tokens[1].upper() == suffix:
            base_symbol = tokens[0]

    # Resolve exchange yahoo suffix
    exchange_upper = exchange.upper().strip()
    yahoo_suffix = EXCHANGE_SUFFIX_MAP.get(exchange_upper, '')

    yahoo_ticker = None
    isin = None
    name = clean_paper
    asset_allocation = None

    # Check known ETF mapping
    if base_symbol in KNOWN_ETF_MAPPING:
        mapping = KNOWN_ETF_MAPPING[base_symbol]
        isin = mapping.get('isin')
        yahoo_ticker = mapping.get('yahoo_ticker')
        name = mapping.get('name', clean_paper)
        asset_allocation = mapping.get('allocation')
    elif len(base_symbol) == 12 and base_symbol[:2].isalpha():
        isin = base_symbol
    else:
        if yahoo_suffix is not None:
            yahoo_ticker = f"{base_symbol}{yahoo_suffix}" if yahoo_suffix else base_symbol

    asset_type = determine_asset_type(clean_paper)
    vault_ticker = f"{base_symbol}_{account_upper}"

    return {
        'base_symbol': base_symbol,
        'vault_ticker': vault_ticker,
        'yahoo_ticker': yahoo_ticker,
        'isin': isin,
        'name': name,
        'asset_type': asset_type,
        'asset_allocation': asset_allocation,
    }


def import_mbm_account(
    csv_file_path: Optional[str] = None,
    account_type: str = "ikze",
    base_dir: Optional[str] = None
) -> Tuple[int, Set[str], Set[str]]:
    """Import positions for a specific mBM account ('ikze' or 'ike').

    Returns:
        (imported_count, active_asset_paths, active_tickers)
    """
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    account_type = account_type.lower().strip()
    account_upper = account_type.upper()
    platform_name = "mBM"
    account_tag = f"#{account_type}"

    mbm_dir = os.path.join(base_dir, "00_Raw", "mBM")
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    csv_file = find_mbm_csv(mbm_dir, account_type=account_type, custom_path=csv_file_path)
    if not csv_file or not os.path.exists(csv_file):
        print(f"Notice: No {account_upper} CSV file found in {mbm_dir}")
        return 0, set(), set()

    print(f"Importing mBM ({account_upper}) positions from: {csv_file}")

    file_date, account_num, rows = parse_mbm_file_content(csv_file)
    current_date = file_date or datetime.now().strftime("%Y-%m-%d")

    template_fm, template_body = load_template(base_dir)

    imported_count = 0
    active_asset_paths: Set[str] = set()
    active_tickers: Set[str] = set()

    for item in rows:
        raw_paper = item['raw_paper']
        exchange = item['exchange']
        quantity = item['quantity']
        price = item['price']
        currency = item['currency']

        info = resolve_instrument_identifiers(raw_paper, exchange, account_type)

        vault_ticker = info['vault_ticker']
        name = info['name']
        isin = info['isin']
        yahoo_ticker = info['yahoo_ticker']
        asset_type = info['asset_type']
        asset_allocation = info['asset_allocation']

        fpath = save_or_update_asset(
            vault_assets_dir=vault_assets_dir,
            platform=platform_name,
            ticker=vault_ticker,
            name=name,
            quantity=quantity,
            current_price=price,
            currency=currency,
            avg_price=None,
            isin=isin,
            current_date=current_date,
            template_fm=template_fm,
            template_body=template_body,
            source='platform',
            portfolio="Long term",
            tags=[account_tag],
            yahoo_ticker=yahoo_ticker,
            asset_allocation=asset_allocation,
            asset_type=asset_type,
        )
        active_asset_paths.add(fpath)
        active_tickers.add(vault_ticker)
        imported_count += 1

    return imported_count, active_asset_paths, active_tickers


def import_mbm_ike(csv_file_path: Optional[str] = None, base_dir: Optional[str] = None) -> int:
    """Import positions from mBM IKE CSV export."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))
    count, paths, tickers = import_mbm_account(csv_file_path=csv_file_path, account_type='ike', base_dir=base_dir)
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    if paths:
        # Clean up missing IKE assets
        for fname in sorted(os.listdir(vault_assets_dir)):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(vault_assets_dir, fname)
            if fpath in paths:
                continue
            if fname.endswith('_IKE.md'):
                try:
                    os.remove(fpath)
                    print(f"Removed missing IKE asset: {fname}")
                except Exception as e:
                    print(f"Warning: could not remove {fname}: {e}")

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return count


def import_mbm_ikze(csv_file_path: Optional[str] = None, base_dir: Optional[str] = None) -> int:
    """Import positions from mBM IKZE CSV export."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))
    count, paths, tickers = import_mbm_account(csv_file_path=csv_file_path, account_type='ikze', base_dir=base_dir)
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    if paths:
        # Clean up missing IKZE assets
        for fname in sorted(os.listdir(vault_assets_dir)):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(vault_assets_dir, fname)
            if fpath in paths:
                continue
            if fname.endswith('_IKZE.md'):
                try:
                    os.remove(fpath)
                    print(f"Removed missing IKZE asset: {fname}")
                except Exception as e:
                    print(f"Warning: could not remove {fname}: {e}")

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return count


def import_mbm(
    csv_file_path: Optional[str] = None,
    account_type: Optional[str] = None,
    base_dir: Optional[str] = None
) -> int:
    """Import positions from mBM CSV export(s) for IKE, IKZE, or both."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")

    # If specific file is given, detect account type from path if not explicitly provided
    if csv_file_path:
        acc = account_type or detect_account_type_from_path(csv_file_path)
        if acc == 'ike':
            return import_mbm_ike(csv_file_path=csv_file_path, base_dir=base_dir)
        else:
            return import_mbm_ikze(csv_file_path=csv_file_path, base_dir=base_dir)

    # If account type is explicitly specified
    if account_type:
        acc = account_type.lower().strip()
        if acc == 'ike':
            return import_mbm_ike(base_dir=base_dir)
        elif acc == 'ikze':
            return import_mbm_ikze(base_dir=base_dir)

    # If neither file nor specific account is specified, import both IKE and IKZE if present
    total = 0
    all_paths: Set[str] = set()
    all_tickers: Set[str] = set()

    print("\n--- Importing mBM (IKZE) ---")
    ikze_count, ikze_paths, ikze_tickers = import_mbm_account(account_type='ikze', base_dir=base_dir)
    total += ikze_count
    all_paths.update(ikze_paths)
    all_tickers.update(ikze_tickers)

    print("\n--- Importing mBM (IKE) ---")
    ike_count, ike_paths, ike_tickers = import_mbm_account(account_type='ike', base_dir=base_dir)
    total += ike_count
    all_paths.update(ike_paths)
    all_tickers.update(ike_tickers)

    # Clean up mBM positions that are no longer active across both accounts (only if at least one file was imported)
    if all_paths:
        remove_missing_platform_assets(
            vault_assets_dir=vault_assets_dir,
            platform='mBM',
            active_asset_paths=all_paths,
            active_tickers=all_tickers,
        )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return total


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import assets from mBM CSV exports (IKE & IKZE).")
    parser.add_argument("-f", "--file", dest="file", type=str, default=None, help="Path to mBM CSV file.")
    parser.add_argument("-a", "--account", dest="account", type=str, choices=["ike", "ikze", "all"], default=None, help="Account type (ike, ikze, all).")
    parser.add_argument("positional_file", nargs="?", default=None, help="Optional mBM CSV file path.")

    args = parser.parse_args()
    target_file = args.file or args.positional_file
    account_type = args.account if args.account != "all" else None
    import_mbm(csv_file_path=target_file, account_type=account_type)


if __name__ == '__main__':
    main()
