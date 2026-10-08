import csv
import os
import sys
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


def update_portfolio_history(base_dir: str | None = None) -> str:
    """Synchronize, deduplicate, and sort all historical portfolio snapshots into 10_Finance/History/portfolio.csv.

    Reads existing entries from portfolio.csv, updates with current state from 10_Finance/Assets/*.md,
    sorts entries chronologically by date and ticker, and writes back cleanly formatted CSV.
    """
    if base_dir is None:
        base_dir = get_base_dir()

    history_dir = os.path.join(base_dir, "10_Finance", "History")
    assets_dir = os.path.join(base_dir, "10_Finance", "Assets")
    os.makedirs(history_dir, exist_ok=True)

    portfolio_file = os.path.join(history_dir, "portfolio.csv")
    old_md_file = os.path.join(history_dir, "portfolio.md")

    fieldnames = ["date", "ticker", "name", "value_pln", "current_price", "pe_ratio", "quantity", "portfolio"]

    # Map of (date, ticker) -> row dict
    entries = {}
    asset_portfolio_map = {}

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
                if date_val and ticker_val:
                    entries[(date_val, ticker_val)] = {
                        "date": date_val,
                        "ticker": ticker_val,
                        "name": (row.get("name") or ticker_val).strip(),
                        "value_pln": format_val(row.get("value_pln")),
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

                    if ticker_val and asset.portfolio:
                        asset_portfolio_map[ticker_val] = asset.portfolio

                    if date_val and ticker_val:
                        entries[(date_val, ticker_val)] = {
                            "date": date_val,
                            "ticker": ticker_val,
                            "name": name_val,
                            "value_pln": format_val(asset.value_pln),
                            "current_price": format_val(asset.current_price),
                            "pe_ratio": format_val(asset.pe_ratio),
                            "quantity": format_val(asset.quantity),
                            "portfolio": format_val(asset.portfolio),
                        }
                except Exception as e:
                    print(f"Warning: could not process asset file {fname}: {e}")

    # Backfill missing portfolio values for historical entries
    for (d, t), item in entries.items():
        if not item.get("portfolio") and t in asset_portfolio_map:
            item["portfolio"] = format_val(asset_portfolio_map[t])

    # 3. Sort entries by date ascending, then ticker ascending
    sorted_entries = sorted(list(entries.values()), key=lambda x: (x["date"], x["ticker"]))

    # 4. Write back to portfolio.csv
    with open(portfolio_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted_entries)

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
