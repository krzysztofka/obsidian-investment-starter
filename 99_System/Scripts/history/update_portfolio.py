import csv
import os
import sys
import tempfile
import time
from datetime import datetime
from typing import Any

# Ensure script root is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from model.asset import Asset


def get_base_dir() -> str:
    """Return the root workspace base directory."""
    return os.path.abspath(os.path.join(script_dir, "../../.."))


def format_val(val: Any) -> str:
    """Format a frontmatter value for CSV export, returning empty string for missing/null values."""
    if val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ("null", "none", "~", ""):
        return ""
    try:
        f = float(val_str)
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return val_str


def atomic_write_csv(
    file_path: str,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
    lineterminator: str = "\n",
    max_retries: int = 5,
    retry_delay: float = 0.2,
) -> None:
    """Atomically write a CSV file using a temporary file and replace with retry backoff.

    Prevents Win32 file lock collisions (Errno 22 / Invalid argument) when Obsidian
    or other background processes hold concurrent read/watch handles on the target file.
    """
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix=".tmp_portfolio_", dir=dir_name, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator=lineterminator)
            writer.writeheader()
            writer.writerows(rows)
            f.flush()
            os.fsync(f.fileno())

        for attempt in range(max_retries):
            try:
                os.replace(temp_path, file_path)
                break
            except (PermissionError, OSError):
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay * (attempt + 1))
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def update_portfolio_history(base_dir: str | None = None) -> str:
    """Synchronize, deduplicate, and sort all historical portfolio snapshots into 10_Finance/History/portfolio.csv.

    Reads existing entries from portfolio.csv, updates with current state from 10_Finance/Assets/*.md,
    reconciles closed/sold positions by recording zero closing entries, sorts chronologically,
    and atomically writes the CSV.
    """
    if base_dir is None:
        base_dir = get_base_dir()

    history_dir = os.path.join(base_dir, "10_Finance", "History")
    assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(history_dir, exist_ok=True)

    portfolio_file = os.path.join(history_dir, "portfolio.csv")
    old_md_file = os.path.join(history_dir, "portfolio.md")

    fieldnames = ["date", "ticker", "name", "value_base", "current_price", "pe_ratio", "quantity", "portfolio"]

    # Map of (date, ticker) -> row dict
    entries = {}
    asset_portfolio_map = {}
    active_tickers = set()
    latest_asset_date = ""

    # Pre-map decisions for sold/historical assets
    decisions_dir = os.path.join(base_dir, "20_Decisions")
    if os.path.exists(decisions_dir):
        for root, _, files in os.walk(decisions_dir):
            for fname in files:
                if fname.endswith(".md"):
                    try:
                        with open(os.path.join(root, fname), encoding="utf-8") as df:
                            content = df.read()
                        import re

                        m_tick = re.search(r'^ticker:\s*["\']?([^"\'\n\r]+)["\']?', content, re.M)
                        m_port = re.search(r'^portfolio:\s*["\']?([^"\'\n\r]+)["\']?', content, re.M)
                        if m_tick and m_port:
                            asset_portfolio_map[m_tick.group(1).strip()] = m_port.group(1).strip()
                    except Exception:
                        pass

    # 1. Read existing entries from portfolio.csv if present
    if os.path.exists(portfolio_file):
        with open(portfolio_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_val = (row.get("date") or "").strip()
                ticker_val = (row.get("ticker") or "").strip()
                val_base_str = row.get("value_base") or row.get("value_pln")
                if date_val and ticker_val:
                    entries[(date_val, ticker_val)] = {
                        "date": date_val,
                        "ticker": ticker_val,
                        "name": (row.get("name") or ticker_val).strip(),
                        "value_base": format_val(val_base_str),
                        "current_price": format_val(row.get("current_price")),
                        "pe_ratio": format_val(row.get("pe_ratio")),
                        "quantity": format_val(row.get("quantity")),
                        "portfolio": format_val(row.get("portfolio")),
                    }

    # 2. Populate / update entries using files in 10_Finance/Assets
    if os.path.exists(assets_dir):
        for fname in os.listdir(assets_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(assets_dir, fname)
                try:
                    asset = Asset.from_file(fpath)
                    date_val = str(asset.last_updated or datetime.now().strftime("%Y-%m-%d")).strip()
                    ticker_val = str(asset.ticker or fname[:-3]).strip()
                    name_val = str(asset.name or ticker_val).strip()

                    if date_val > latest_asset_date:
                        latest_asset_date = date_val

                    # Track active holdings with positive value / quantity
                    val_float = 0.0
                    val_candidate = asset.value_base if asset.value_base is not None else asset.value_pln
                    if val_candidate is not None:
                        try:
                            val_float = float(val_candidate)
                        except (ValueError, TypeError):
                            val_float = 0.0

                    if val_float > 0:
                        active_tickers.add(ticker_val)

                    if ticker_val and asset.portfolio:
                        asset_portfolio_map[ticker_val] = asset.portfolio

                    if date_val and ticker_val:
                        entries[(date_val, ticker_val)] = {
                            "date": date_val,
                            "ticker": ticker_val,
                            "name": name_val,
                            "value_base": format_val(val_candidate),
                            "current_price": format_val(asset.current_price),
                            "pe_ratio": format_val(asset.pe_ratio),
                            "quantity": format_val(asset.quantity),
                            "portfolio": format_val(asset.portfolio),
                        }
                except Exception as e:
                    print(f"Warning: could not process asset file {fname}: {e}")

    # 2.5 Reconcile sold / missing positions: ensure any ticker previously active
    # that is no longer held (missing from active assets or zeroed) receives a closing 0 row.
    all_dates = sorted(list({d for (d, _) in entries.keys()}))
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_snapshot_date = max(today_str, latest_asset_date) if latest_asset_date else today_str

    ticker_dates_map: dict[str, list[str]] = {}
    for d, t in entries.keys():
        ticker_dates_map.setdefault(t, []).append(d)

    for t, t_dates in sorted(ticker_dates_map.items()):
        if t in active_tickers:
            continue
        sorted_t_dates = sorted(t_dates)
        last_t_date = sorted_t_dates[-1]
        last_entry = entries[(last_t_date, t)]

        try:
            last_val = float(last_entry.get("value_base") or last_entry.get("value_pln") or 0)
        except (ValueError, TypeError):
            last_val = 0.0

        if last_val > 0:
            # Position ceased to exist after last_t_date. Find next chronological snapshot date.
            subsequent_dates = [d for d in all_dates if d > last_t_date]
            if subsequent_dates:
                close_date = subsequent_dates[0]
            else:
                close_date = current_snapshot_date

            if close_date == last_t_date:
                last_entry["value_base"] = "0"
                last_entry["quantity"] = "0"
                last_entry["current_price"] = "0"
            else:
                entries[(close_date, t)] = {
                    "date": close_date,
                    "ticker": t,
                    "name": last_entry.get("name") or t,
                    "value_base": "0",
                    "current_price": "0",
                    "pe_ratio": "",
                    "quantity": "0",
                    "portfolio": last_entry.get("portfolio") or asset_portfolio_map.get(t, ""),
                }

    # Backfill missing portfolio values for historical entries
    for (d, t), item in entries.items():
        if not item.get("portfolio") and t in asset_portfolio_map:
            item["portfolio"] = format_val(asset_portfolio_map[t])

    # 3. Sort entries by date ascending, then ticker ascending
    sorted_entries = sorted(list(entries.values()), key=lambda x: (x["date"], x["ticker"]))

    # 4. Atomically write back to portfolio.csv
    atomic_write_csv(portfolio_file, fieldnames, sorted_entries)

    # Clean up legacy portfolio.md if it exists
    if os.path.exists(old_md_file):
        try:
            os.remove(old_md_file)
        except Exception:
            pass

    print(f"Updated portfolio history at {portfolio_file} ({len(sorted_entries)} total entries).")

    # 5. Automatically execute portfolio history archival if enabled
    try:
        from history.retention import archive_portfolio_history

        archive_portfolio_history(base_dir=base_dir)
    except Exception as e:
        print(f"Notice: Portfolio history archival skipped or encountered an error: {e}")

    return portfolio_file


def main():
    base_dir = get_base_dir()
    update_portfolio_history(base_dir)


if __name__ == "__main__":
    main()
