"""PKO BP Treasury Retail Bonds Platform Extension."""

import fnmatch
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
from model.config import load_vault_config

from platforms.base import BasePlatform, PlatformRegistry
from platforms.common import (
    load_template,
    parse_number,
    remove_missing_platform_assets,
    save_or_update_assets_parallel,
)


def format_maturity_date_yyyymmdd(maturity_str: str | None) -> str | None:
    """Format maturity date into YYYYMMDD string format."""
    if not maturity_str:
        return None
    s = str(maturity_str).strip()
    m = re.match(r"^(\d{4})[^\d]?(\d{2})[^\d]?(\d{2})$", s)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    m = re.match(r"^(\d{2})[^\d](\d{2})[^\d](\d{4})$", s)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        return digits
    return None


def load_pkobp_config(base_dir: str | None = None) -> dict[str, Any]:
    """Load PKO BP bonds configuration rules from config.yaml."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    try:
        vault_cfg = load_vault_config(base_dir=base_dir)
        p_cfg = vault_cfg.platforms.get("pko_bp_bonds") or vault_cfg.platforms.get("pkobp")
        if p_cfg:
            return p_cfg.model_dump()
    except Exception:
        pass

    return {
        "enabled": True,
        "default_mode": "xls",
        "default_portfolio": "Long term",
        "rules": [
            {"ticker": "EDO0936", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "ROD", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "ROK", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "OTS", "portfolio": "Safety net"},
            {"prefix": "ROR", "portfolio": "Safety net"},
        ],
    }


def find_pkobp_file(raw_dir: str, custom_path: str | None = None, fallback_dir: str | None = None) -> str | None:
    """Find target PKO BP export file (.xls or .xlsx)."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    candidates_dirs = [raw_dir]
    if fallback_dir and os.path.exists(fallback_dir) and fallback_dir != raw_dir:
        candidates_dirs.append(fallback_dir)

    for d in candidates_dirs:
        if not os.path.exists(d):
            continue
        files = [
            os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".xls", ".xlsx")) and not f.startswith("~")
        ]
        if files:

            def file_sort_key(filepath: str):
                m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(filepath))
                date_str = m.group(0) if m else ""
                return (date_str, os.path.getmtime(filepath))

            files.sort(key=file_sort_key, reverse=True)
            return files[0]

    return None


def parse_pkobp_sheet(file_path: str) -> list[dict[str, Any]]:
    """Parse positions from PKO BP register status Excel file."""
    import xlrd

    wb = xlrd.open_workbook(file_path)
    sheet = wb.sheet_by_index(0)

    if sheet.nrows < 2:
        return []

    header_row_idx = -1
    for r in range(min(10, sheet.nrows)):
        row_vals = [str(sheet.cell_value(r, c)).strip().upper() for c in range(sheet.ncols)]
        if any("EMISJA" in v for v in row_vals):
            header_row_idx = r
            break

    if header_row_idx == -1:
        raise ValueError(f"Could not find valid header row with 'EMISJA' column in {file_path}")

    headers = [str(sheet.cell_value(header_row_idx, c)).strip().upper() for c in range(sheet.ncols)]

    def find_col(possible_names: list[str]) -> int | None:
        for idx, h in enumerate(headers):
            for name in possible_names:
                if name.upper() in h:
                    return idx
        return None

    col_emission = find_col(["EMISJA"])
    col_qty_avail = find_col(["DOSTĘPNA LICZBA", "DOSTEPNA LICZBA", "LICZBA OBLIGACJI", "ILOŚĆ", "ILOSC"])
    col_qty_blocked = find_col(["ZABLOKOWANA LICZBA"])
    col_nom_val = find_col(["WARTOŚĆ NOMINALNA", "WARTOSC NOMINALNA", "NOMINAŁ", "NOMINAL"])
    col_curr_val = find_col(["WARTOŚĆ AKTUALNA", "WARTOSC AKTUALNA", "WARTOŚĆ RYNKOWA", "WARTOSC"])
    col_maturity = find_col(["DATA WYKUPU", "WYKUP", "TERMIN WYKUPU"])

    rows: list[dict[str, Any]] = []
    for r in range(header_row_idx + 1, sheet.nrows):
        emission = str(sheet.cell_value(r, col_emission)).strip() if col_emission is not None else ""
        if not emission or emission.upper().startswith("SUMA") or emission.upper().startswith("RAZEM"):
            continue

        qty_avail = parse_number(sheet.cell_value(r, col_qty_avail)) if col_qty_avail is not None else 0
        qty_blocked = parse_number(sheet.cell_value(r, col_qty_blocked)) if col_qty_blocked is not None else 0
        total_qty = qty_avail + qty_blocked

        if total_qty <= 0:
            continue

        nom_val = parse_number(sheet.cell_value(r, col_nom_val)) if col_nom_val is not None else 0
        curr_val = parse_number(sheet.cell_value(r, col_curr_val)) if col_curr_val is not None else 0

        maturity_val = sheet.cell_value(r, col_maturity) if col_maturity is not None else ""
        if isinstance(maturity_val, float):
            try:
                date_tuple = xlrd.xldate_as_tuple(maturity_val, wb.datemode)
                maturity_str = f"{date_tuple[0]:04d}-{date_tuple[1]:02d}-{date_tuple[2]:02d}"
            except Exception:
                maturity_str = str(maturity_val)
        else:
            maturity_str = str(maturity_val).strip()

        rows.append(
            {
                "emission": emission,
                "quantity": total_qty,
                "nominal_value": nom_val if nom_val > 0 else total_qty * 100.0,
                "current_value": curr_val if curr_val > 0 else (nom_val if nom_val > 0 else total_qty * 100.0),
                "maturity_date": maturity_str,
            }
        )

    return rows


def resolve_portfolio_allocation(
    emission: str,
    total_qty: int | float,
    nominal_val: int | float,
    current_val: int | float,
    config: dict[str, Any],
    maturity_date: str | None = None,
) -> list[dict[str, Any]]:
    """Determine how many units/amount of an emission go into which portfolio based on config rules.

    Returns a list of dicts, each representing a position slice:
      [{'ticker': '...', 'name': '...', 'portfolio': '...', 'quantity': ..., 'current_price': ..., 'value_pln': ...}]
    """
    default_portfolio = config.get("default_portfolio", "Long term")
    rules = config.get("rules", [])

    price_per_unit = (current_val / total_qty) if total_qty > 0 else 100.0
    nominal_price_per_unit = (nominal_val / total_qty) if total_qty > 0 else 100.0

    maturity_compact = format_maturity_date_yyyymmdd(maturity_date)
    ticker_base = f"{emission}_{maturity_compact}" if maturity_compact else emission

    matched_rule = None
    emission_upper = emission.strip().upper()
    ticker_base_upper = ticker_base.strip().upper()

    for rule in rules:
        r_ticker = rule.get("ticker")
        if r_ticker and (r_ticker.strip().upper() == emission_upper or r_ticker.strip().upper() == ticker_base_upper):
            matched_rule = rule
            break

        r_prefix = rule.get("prefix")
        if r_prefix and (
            emission_upper.startswith(r_prefix.strip().upper())
            or ticker_base_upper.startswith(r_prefix.strip().upper())
        ):
            matched_rule = rule
            break

        r_series = rule.get("series")
        if r_series and (
            fnmatch.fnmatch(emission_upper, r_series.strip().upper())
            or fnmatch.fnmatch(ticker_base_upper, r_series.strip().upper())
            or r_series.strip().upper() in emission_upper
        ):
            matched_rule = rule
            break

    if not matched_rule:
        return [
            {
                "ticker": ticker_base,
                "name": ticker_base,
                "portfolio": default_portfolio,
                "quantity": total_qty,
                "current_price": round(price_per_unit, 2),
                "value_pln": round(current_val, 2),
            }
        ]

    target_portfolio = matched_rule.get("portfolio", default_portfolio)
    overflow_portfolio = matched_rule.get("overflow_portfolio", default_portfolio)

    max_amount = matched_rule.get("max_amount")
    max_qty = matched_rule.get("max_quantity")

    rule_qty_limit = None
    if max_qty is not None:
        rule_qty_limit = parse_number(max_qty)
    elif max_amount is not None:
        amount_limit = parse_number(max_amount)
        rule_qty_limit = amount_limit / nominal_price_per_unit

    if rule_qty_limit is None or total_qty <= rule_qty_limit:
        return [
            {
                "ticker": ticker_base,
                "name": ticker_base,
                "portfolio": target_portfolio,
                "quantity": total_qty,
                "current_price": round(price_per_unit, 2),
                "value_pln": round(current_val, 2),
            }
        ]

    rule_qty = int(rule_qty_limit) if float(rule_qty_limit).is_integer() else rule_qty_limit
    overflow_qty = total_qty - rule_qty

    rule_val = round(rule_qty * price_per_unit, 2)
    overflow_val = round(overflow_qty * price_per_unit, 2)

    safe_target = target_portfolio.replace(" ", "_")
    safe_overflow = overflow_portfolio.replace(" ", "_")

    return [
        {
            "ticker": f"{ticker_base}_{safe_target}",
            "name": f"{ticker_base} ({target_portfolio})",
            "portfolio": target_portfolio,
            "quantity": rule_qty,
            "current_price": round(price_per_unit, 2),
            "value_pln": rule_val,
        },
        {
            "ticker": f"{ticker_base}_{safe_overflow}",
            "name": f"{ticker_base} ({overflow_portfolio})",
            "portfolio": overflow_portfolio,
            "quantity": overflow_qty,
            "current_price": round(price_per_unit, 2),
            "value_pln": overflow_val,
        },
    ]


def import_pko_bp_bonds(
    file_path: str | None = None,
    base_dir: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> int:
    """Import positions from PKO BP retail treasury bond Excel file."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(parent_scripts_dir, "../.."))

    raw_dir = os.path.join(base_dir, "00_Raw", "pko_bp_bonds")
    legacy_raw_dir = os.path.join(base_dir, "00_Raw", "pkobp")
    vault_assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(vault_assets_dir, exist_ok=True)

    target_file = find_pkobp_file(raw_dir, custom_path=file_path, fallback_dir=legacy_raw_dir)
    if not target_file or not os.path.exists(target_file):
        print(f"Notice: No PKO BP Excel file found in {raw_dir}")
        return 0

    print(f"Importing PKO BP retail bonds from: {target_file}")

    filename = os.path.basename(target_file)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
    current_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

    config = load_pkobp_config(base_dir)
    rows = parse_pkobp_sheet(target_file)
    template_fm, _ = load_template(base_dir)

    asset_tasks = []
    for item in rows:
        emission = item["emission"]
        total_qty = item["quantity"]
        nom_val = item["nominal_value"]
        curr_val = item["current_value"]
        maturity = item["maturity_date"]

        slices = resolve_portfolio_allocation(
            emission=emission,
            total_qty=total_qty,
            nominal_val=nom_val,
            current_val=curr_val,
            config=config,
            maturity_date=maturity,
        )

        for sl in slices:
            ticker = sl["ticker"]
            name = sl["name"]
            portfolio = sl["portfolio"]
            qty = sl["quantity"]
            cur_price = sl["current_price"]

            bond_body = f"\n# Polish government bonds ({name})\n\n**Platform:** [[PKOBP]]\n"
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

            asset_tasks.append(
                {
                    "vault_assets_dir": vault_assets_dir,
                    "platform": "PKOBP",
                    "ticker": ticker,
                    "name": name,
                    "quantity": qty,
                    "current_price": cur_price,
                    "currency": "PLN",
                    "avg_price": 100.0,
                    "isin": None,
                    "current_date": current_date,
                    "template_fm": template_fm,
                    "template_body": bond_body,
                    "source": "platform",
                    "portfolio": portfolio,
                    "asset_type": "bond",
                    "asset_allocation": {"bonds": 100},
                    "dominant_sector": "Sovereign",
                    "industry": "Sovereign",
                    "sector": "Sovereign",
                    "stooq_ticker": "10ply.b",
                    "country": "Poland",
                }
            )

    active_asset_paths, active_tickers, imported_count = save_or_update_assets_parallel(
        asset_tasks=asset_tasks,
        max_workers=max_workers,
        base_dir=base_dir,
        show_progress=show_progress,
    )

    remove_missing_platform_assets(
        vault_assets_dir=vault_assets_dir,
        platform="PKOBP",
        active_asset_paths=active_asset_paths,
        active_tickers=active_tickers,
    )

    print("\nUpdating portfolio history...")
    update_portfolio_history(base_dir)
    return imported_count


# Backward compatibility alias
import_pkobp = import_pko_bp_bonds


@PlatformRegistry.register
class PkoBpBondsPlatform(BasePlatform):
    """PKO BP Treasury Retail Bonds Platform Extension."""

    id = "pko_bp_bonds"
    display_name = "PKO BP (Bonds)"
    raw_folder = "pko_bp_bonds"
    default_mode = "xls"
    aliases = ["pkobp", "pko", "pko_bp"]

    def can_handle_file(self, file_path: str) -> bool:
        norm = os.path.normpath(file_path).lower()
        if "pko_bp_bonds" in norm or "pkobp" in norm or "stanrachunku" in norm:
            return True
        if "pko" in norm and norm.endswith((".xls", ".xlsx")):
            return True
        return False

    def run_import(
        self,
        file_path: str | None = None,
        use_api: bool | None = None,
        account_id: str | None = None,
        max_workers: int | None = None,
        show_progress: bool = True,
    ) -> int:
        return import_pko_bp_bonds(
            file_path=file_path,
            base_dir=self.base_dir,
            max_workers=max_workers,
            show_progress=show_progress,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import PKO BP treasury retail bonds.")
    parser.add_argument("-f", "--file", dest="file", type=str, default=None, help="Path to PKO BP Excel file.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of worker threads.")
    parser.add_argument("positional_file", nargs="?", default=None, help="Optional PKO BP Excel file path.")

    args = parser.parse_args()
    target_file = args.file or args.positional_file
    import_pko_bp_bonds(file_path=target_file, max_workers=args.max_workers)
