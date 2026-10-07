"""Common parser utilities and mappings for mBank (eMakler / mBM) platforms."""

import os
import re
import sys
from datetime import datetime
from typing import Any

# Ensure scripts directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from history.update_portfolio import update_portfolio_history

from platforms.common import (
    determine_asset_type,
    ensure_utf8_file,
    load_template,
    parse_number,
    save_or_update_assets_parallel,
)

KNOWN_ETF_MAPPING: dict[str, dict[str, Any]] = {
    "V80A": {
        "isin": "IE00BMVB5R75",
        "yahoo_ticker": "V80A.DE",
        "name": "Vanguard LifeStrategy 80% Equity UCITS ETF",
        "allocation": {"equity": 80, "bonds": 20, "cash": 0},
    },
    "VNGA80": {
        "isin": "IE00BMVB5R75",
        "yahoo_ticker": "V80A.DE",
        "name": "Vanguard LifeStrategy 80% Equity UCITS ETF",
        "allocation": {"equity": 80, "bonds": 20, "cash": 0},
    },
    "V60A": {
        "isin": "IE00BMVB5P51",
        "yahoo_ticker": "V60A.DE",
        "name": "Vanguard LifeStrategy 60% Equity UCITS ETF",
        "allocation": {"equity": 60, "bonds": 40, "cash": 0},
    },
    "VNGA60": {
        "isin": "IE00BMVB5P51",
        "yahoo_ticker": "V60A.DE",
        "name": "Vanguard LifeStrategy 60% Equity UCITS ETF",
        "allocation": {"equity": 60, "bonds": 40, "cash": 0},
    },
    "V40A": {
        "isin": "IE00BMVB5M21",
        "yahoo_ticker": "V40A.DE",
        "name": "Vanguard LifeStrategy 40% Equity UCITS ETF",
        "allocation": {"equity": 40, "bonds": 60, "cash": 0},
    },
    "VNGA40": {
        "isin": "IE00BMVB5M21",
        "yahoo_ticker": "V40A.DE",
        "name": "Vanguard LifeStrategy 40% Equity UCITS ETF",
        "allocation": {"equity": 40, "bonds": 60, "cash": 0},
    },
    "V20A": {
        "isin": "IE00BMVB5K07",
        "yahoo_ticker": "V20A.DE",
        "name": "Vanguard LifeStrategy 20% Equity UCITS ETF",
        "allocation": {"equity": 20, "bonds": 80, "cash": 0},
    },
    "VNGA20": {
        "isin": "IE00BMVB5K07",
        "yahoo_ticker": "V20A.DE",
        "name": "Vanguard LifeStrategy 20% Equity UCITS ETF",
        "allocation": {"equity": 20, "bonds": 80, "cash": 0},
    },
    "VWCE": {
        "isin": "IE00BK5BQT80",
        "yahoo_ticker": "VWCE.DE",
        "name": "Vanguard FTSE All-World UCITS ETF (USD) Accumulating",
    },
    "VWRL": {
        "isin": "IE00B3RBWM25",
        "yahoo_ticker": "VWRL.DE",
        "name": "Vanguard FTSE All-World UCITS ETF (USD) Distributing",
    },
    "SPPW": {
        "isin": "IE00BFY0GT14",
        "yahoo_ticker": "SPPW.DE",
        "name": "SPDR MSCI World UCITS ETF",
    },
    "SXR8": {
        "isin": "IE00B5BMR087",
        "yahoo_ticker": "SXR8.DE",
        "name": "iShares Core S&P 500 UCITS ETF (Acc)",
    },
    "EUNL": {
        "isin": "IE00B4L5Y983",
        "yahoo_ticker": "EUNL.DE",
        "name": "iShares Core MSCI World UCITS ETF (Acc)",
    },
    "IS3N": {
        "isin": "IE00BKM4GZ66",
        "yahoo_ticker": "IS3N.DE",
        "name": "iShares Core MSCI Emerging Markets IMI UCITS ETF (Acc)",
    },
    "QDVE": {
        "isin": "IE00B3WJKG14",
        "yahoo_ticker": "QDVE.DE",
        "name": "iShares S&P 500 Information Technology Sector UCITS ETF",
    },
    "SXRV": {
        "isin": "IE00B53SZB19",
        "yahoo_ticker": "SXRV.DE",
        "name": "iShares NASDAQ 100 UCITS ETF (Acc)",
    },
    "DBX0AN": {
        "isin": "LU0290358497",
        "yahoo_ticker": "DBX0AN.DE",
        "name": "Xtrackers II EUR Overnight Rate Swap UCITS ETF",
    },
    "XEON": {
        "isin": "LU0290358497",
        "yahoo_ticker": "XEON.DE",
        "name": "Xtrackers II EUR Overnight Rate Swap UCITS ETF",
    },
}

EXCHANGE_SUFFIX_MAP = {
    "DEU-XETRA": ".DE",
    "DEU-FRA": ".F",
    "GPW-AKCJE": ".WA",
    "GPW-ETF": ".WA",
    "GPW": ".WA",
    "WSE": ".WA",
    "USA-NASDAQ": "",
    "USA-NYSE": "",
    "USA": "",
    "LSE": ".L",
    "EURONEXT-AMS": ".AS",
    "EURONEXT-PAR": ".PA",
}


def find_account_csv(
    account_dir: str,
    account_type: str,
    custom_path: str | None = None,
    fallback_dir: str | None = None,
) -> str | None:
    """Find the most recent CSV file for a given mBank account type ('ike' or 'ikze')."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    target_type = account_type.lower()

    # 1. Search in dedicated directory: all .csv files count
    if os.path.exists(account_dir):
        files = [os.path.join(account_dir, f) for f in os.listdir(account_dir) if f.lower().endswith(".csv")]
        if files:

            def file_sort_key(filepath: str):
                m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(filepath))
                date_str = m.group(0) if m else ""
                return (date_str, os.path.getmtime(filepath))

            files.sort(key=file_sort_key, reverse=True)
            return files[0]

    # 2. Search in legacy fallback directory (00_Raw/mBM): filter by account_type keyword
    if fallback_dir and os.path.exists(fallback_dir) and fallback_dir != account_dir:
        candidates = []
        for f in os.listdir(fallback_dir):
            if not f.lower().endswith(".csv"):
                continue
            fname_lower = f.lower()
            if target_type == "ikze" and "ikze" in fname_lower:
                candidates.append(os.path.join(fallback_dir, f))
            elif target_type == "ike" and "ike" in fname_lower and "ikze" not in fname_lower:
                candidates.append(os.path.join(fallback_dir, f))

        if candidates:

            def file_sort_key(filepath: str):
                m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(filepath))
                date_str = m.group(0) if m else ""
                return (date_str, os.path.getmtime(filepath))

            candidates.sort(key=file_sort_key, reverse=True)
            return candidates[0]

    return None


def parse_mbm_file_content(file_path: str) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    """Read mBank CSV file and parse positions."""
    raw_content = ensure_utf8_file(file_path)
    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]

    file_date = None
    account_number = None

    for i, line in enumerate(lines):
        if line.startswith("#Data") and i + 1 < len(lines):
            d_val = lines[i + 1].strip()
            d_match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", d_val)
            if d_match:
                file_date = f"{d_match.group(3)}-{d_match.group(2)}-{d_match.group(1)}"
        elif line.startswith("#Nr rachunku") and i + 1 < len(lines):
            account_number = lines[i + 1].strip()

    if not file_date:
        fn_match = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(file_path))
        if fn_match:
            file_date = fn_match.group(0)

    header_idx = None
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if "papier" in line_lower and ("giełda" in line_lower or "gielda" in line_lower or "kurs" in line_lower):
            header_idx = i
            break

    if header_idx is None:
        return file_date, account_number, []

    headers = [h.strip() for h in lines[header_idx].split(";")]
    col_paper = next((i for i, h in enumerate(headers) if h.lower() in ["papier", "instrument", "nazwa"]), None)
    col_exchange = next((i for i, h in enumerate(headers) if h.lower() in ["giełda", "gielda", "rynek"]), None)
    col_qty = next(
        (
            i
            for i, h in enumerate(headers)
            if any(k in h.lower() for k in ["liczba", "ilość", "ilosc", "suma", "quantity"])
        ),
        None,
    )
    col_price = next((i for i, h in enumerate(headers) if h.lower() in ["kurs", "cena", "price"]), None)

    currency_indices = [i for i, h in enumerate(headers) if h.lower() in ["waluta", "currency"]]
    col_curr = currency_indices[0] if currency_indices else None

    parsed_rows: list[dict[str, Any]] = []

    for line in lines[header_idx + 1 :]:
        if not line or ";" not in line:
            continue
        parts = [p.strip() for p in line.split(";")]
        valid_indices = [x for x in [col_paper, col_qty, col_price] if x is not None]
        if not valid_indices or len(parts) <= max(valid_indices):
            continue

        raw_paper = parts[col_paper] if col_paper is not None else ""
        if not raw_paper:
            continue

        if any(
            term in raw_paper.lower() for term in ["łączna wycena", "laczna wycena", "suma", "razem", "podsumowanie"]
        ):
            break

        exchange = parts[col_exchange] if col_exchange is not None and col_exchange < len(parts) else ""
        raw_qty = parts[col_qty] if col_qty is not None and col_qty < len(parts) else "0"
        raw_price = parts[col_price] if col_price is not None and col_price < len(parts) else "0"
        currency = parts[col_curr] if col_curr is not None and col_curr < len(parts) else "PLN"

        qty_match = re.match(r"([\d\s,.]+)(?:\s*\(([\d\s,.]+)\))?", raw_qty)
        if qty_match:
            avail = parse_number(qty_match.group(1))
            blocked = parse_number(qty_match.group(2)) if qty_match.group(2) else 0
            quantity = avail + blocked
        else:
            quantity = parse_number(raw_qty)

        price = parse_number(raw_price)

        if quantity <= 0:
            continue

        parsed_rows.append(
            {
                "raw_paper": raw_paper,
                "exchange": exchange,
                "quantity": quantity,
                "price": price,
                "currency": currency,
            }
        )

    return file_date, account_number, parsed_rows


def resolve_instrument_identifiers(raw_paper: str, exchange: str, account_type: str) -> dict[str, Any]:
    """Resolve base ticker, vault ticker, yahoo ticker, ISIN, name, and asset properties."""
    clean_paper = raw_paper.strip()
    account_upper = account_type.upper()

    tokens = clean_paper.split()
    first_token = tokens[0] if tokens else clean_paper

    base_symbol = first_token
    for suffix in ["GR", "GY", "LN", "US", "FP", "NA", "SW", "PW", "ETF", "UCITS", "ETC", "ETN"]:
        if len(tokens) > 1 and tokens[1].upper() == suffix:
            base_symbol = tokens[0]

    exchange_upper = exchange.upper().strip()
    yahoo_suffix = EXCHANGE_SUFFIX_MAP.get(exchange_upper, "")

    yahoo_ticker = None
    isin = None
    name = clean_paper
    asset_allocation = None

    if base_symbol in KNOWN_ETF_MAPPING:
        mapping = KNOWN_ETF_MAPPING[base_symbol]
        isin = mapping.get("isin")
        yahoo_ticker = mapping.get("yahoo_ticker")
        name = mapping.get("name", clean_paper)
        asset_allocation = mapping.get("allocation")
    elif len(base_symbol) == 12 and base_symbol[:2].isalpha():
        isin = base_symbol
    else:
        if yahoo_suffix is not None:
            yahoo_ticker = f"{base_symbol}{yahoo_suffix}" if yahoo_suffix else base_symbol

    asset_type = determine_asset_type(clean_paper)
    vault_ticker = f"{base_symbol}_{account_upper}"

    return {
        "base_symbol": base_symbol,
        "vault_ticker": vault_ticker,
        "yahoo_ticker": yahoo_ticker,
        "isin": isin,
        "name": name,
        "asset_type": asset_type,
        "asset_allocation": asset_allocation,
    }


def import_mbank_account_positions(
    csv_file_path: str | None,
    account_type: str,
    raw_folder_name: str,
    base_dir: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> int:
    """Import positions for a specific mBank account ('ike' or 'ikze')."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    account_type = account_type.lower().strip()
    account_upper = account_type.upper()
    platform_name = "mBM"
    account_tag = f"#{account_type}"

    account_dir = os.path.join(base_dir, "00_Raw", raw_folder_name)
    legacy_dir = os.path.join(base_dir, "00_Raw", "mBM")
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    csv_file = find_account_csv(
        account_dir, account_type=account_type, custom_path=csv_file_path, fallback_dir=legacy_dir
    )
    if not csv_file or not os.path.exists(csv_file):
        print(f"Notice: No {account_upper} CSV file found in {account_dir}")
        return 0

    print(f"Importing mBank ({account_upper}) positions from: {csv_file}")

    file_date, account_num, rows = parse_mbm_file_content(csv_file)
    current_date = file_date or datetime.now().strftime("%Y-%m-%d")

    template_fm, template_body = load_template(base_dir)

    asset_tasks = []
    for item in rows:
        raw_paper = item["raw_paper"]
        exchange = item["exchange"]
        quantity = item["quantity"]
        price = item["price"]
        currency = item["currency"]

        info = resolve_instrument_identifiers(raw_paper, exchange, account_type)

        vault_ticker = info["vault_ticker"]
        name = info["name"]
        isin = info["isin"]
        yahoo_ticker = info["yahoo_ticker"]
        asset_type = info["asset_type"]
        asset_allocation = info["asset_allocation"]

        asset_tasks.append(
            {
                "vault_assets_dir": vault_assets_dir,
                "platform": platform_name,
                "ticker": vault_ticker,
                "name": name,
                "quantity": quantity,
                "current_price": price,
                "currency": currency,
                "avg_price": None,
                "isin": isin,
                "current_date": current_date,
                "template_fm": template_fm,
                "template_body": template_body,
                "source": "platform",
                "portfolio": "Long term",
                "tags": [account_tag],
                "yahoo_ticker": yahoo_ticker,
                "asset_allocation": asset_allocation,
                "asset_type": asset_type,
            }
        )

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    # Clean up obsolete assets for this account type
    suffix = f"_{account_type}.md"
    for fname in sorted(os.listdir(vault_assets_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(vault_assets_dir, fname)
        if fpath in active_asset_paths:
            continue
        if fname.lower().endswith(suffix):
            try:
                os.remove(fpath)
                print(f"Removed missing {account_upper} asset: {fname}")
            except Exception as e:
                print(f"Warning: could not remove {fname}: {e}")

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


def detect_account_type_from_path(file_path: str) -> str:
    """Detect whether file corresponds to IKE or IKZE based on path and file name."""
    norm = file_path.lower()
    if "ikze" in norm:
        return "ikze"
    if "ike" in norm:
        return "ike"
    return "ikze"


def find_mbm_csv(mbm_dir: str, account_type: str | None = None, custom_path: str | None = None) -> str | None:
    """Find CSV file for mBM."""
    acc = account_type or "ikze"
    return find_account_csv(account_dir=mbm_dir, account_type=acc, custom_path=custom_path)


def import_mbm(
    csv_file_path: str | None = None,
    account_type: str | None = None,
    base_dir: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> int:
    """Import positions from mBM CSV export(s) for IKE, IKZE, or both."""
    from platforms.mbank_ike import import_mbm_ike
    from platforms.mbank_ikze import import_mbm_ikze

    if csv_file_path:
        acc = account_type or detect_account_type_from_path(csv_file_path)
        if acc == "ike":
            return import_mbm_ike(
                csv_file_path=csv_file_path, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress
            )
        else:
            return import_mbm_ikze(
                csv_file_path=csv_file_path, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress
            )

    if account_type:
        acc = account_type.lower().strip()
        if acc == "ike":
            return import_mbm_ike(base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        elif acc == "ikze":
            return import_mbm_ikze(base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)

    # Both
    c_ikze = import_mbm_ikze(base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
    c_ike = import_mbm_ike(base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
    return c_ikze + c_ike
