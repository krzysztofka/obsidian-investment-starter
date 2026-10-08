"""Data Retention & History Archival Engine.

Provides automated and configurable retention and archival policies:
1. Portfolio history archival: retains rolling 2-year daily records in portfolio.csv,
   moving older records to partitioned yearly archives (history-archive-YYYY.csv)
   with boundary baseline preservation for continuous dashboard valuation.
2. Ephemeral raw data rotation: safely archives or prunes raw broker exports older than 1 year
   with checksum-aware collision handling and strict protection of sample/system files.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from typing import Any

# Ensure script root is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from logging_util import get_logger
from model.config import HistoryRetentionConfig, RawDataRetentionConfig, load_vault_config

logger = get_logger("retention")

PORTFOLIO_FIELDS = [
    "date",
    "ticker",
    "name",
    "value_pln",
    "current_price",
    "pe_ratio",
    "quantity",
    "portfolio",
]


def get_base_dir() -> str:
    """Return the root workspace base directory."""
    return os.path.abspath(os.path.join(script_dir, "../../.."))


def compute_file_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_date_from_filename(filename: str) -> datetime | None:
    """Extract a date from filename pattern (YYYY-MM-DD, YYYY_MM_DD, or YYYYMMDD)."""
    # 1. Hyphen or underscore separated: YYYY-MM-DD or YYYY_MM_DD
    m = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", filename)
    if m:
        try:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day)
        except ValueError:
            pass

    # 2. Compact YYYYMMDD preceded/followed by non-digit or boundary
    m = re.search(r"(?:^|[^0-9])(\d{4})(\d{2})(\d{2})(?:[^0-9]|$)", filename)
    if m:
        try:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day)
        except ValueError:
            pass

    return None


def archive_portfolio_history(
    base_dir: str | None = None,
    retention_days: int | None = None,
    dry_run: bool = False,
    preserve_baseline: bool | None = None,
) -> dict[str, Any]:
    """Archive portfolio.csv records older than retention_days into yearly archives.

    Retains records within the rolling window (date >= cutoff) in portfolio.csv.
    Carries over a baseline snapshot at cutoff_date if preserve_baseline is True,
    ensuring continuous forward-fill in Portfolio_performance.md.
    """
    if base_dir is None:
        base_dir = get_base_dir()

    vault_cfg = load_vault_config(base_dir=base_dir)
    cfg: HistoryRetentionConfig = vault_cfg.retention.history

    if not cfg.enabled:
        logger.info("Portfolio history retention is disabled in config.yaml.")
        return {"status": "disabled", "archived_count": 0, "retained_count": 0}

    days = retention_days if retention_days is not None else cfg.retention_days
    should_preserve = preserve_baseline if preserve_baseline is not None else cfg.preserve_boundary_baseline

    history_dir = os.path.join(base_dir, "10_Finance", "History")
    portfolio_file = os.path.join(history_dir, "portfolio.csv")
    archive_dir = os.path.join(base_dir, cfg.archive_dir)

    if not os.path.exists(portfolio_file):
        logger.info(f"portfolio.csv not found at {portfolio_file}, skipping archival.")
        return {"status": "not_found", "archived_count": 0, "retained_count": 0}

    # Load existing rows from portfolio.csv
    rows: list[dict[str, str]] = []
    with open(portfolio_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("date") and r.get("ticker"):
                rows.append({k: (r.get(k) or "").strip() for k in PORTFOLIO_FIELDS})

    if not rows:
        return {"status": "empty", "archived_count": 0, "retained_count": 0}

    cutoff_dt = datetime.now() - timedelta(days=days)
    cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    archived_rows: list[dict[str, str]] = []
    retained_rows: list[dict[str, str]] = []

    for r in rows:
        if r["date"] < cutoff_date:
            archived_rows.append(r)
        else:
            retained_rows.append(r)

    if not archived_rows:
        logger.info(f"No portfolio records older than {cutoff_date} ({days} days) found to archive.")
        return {
            "status": "up_to_date",
            "archived_count": 0,
            "retained_count": len(retained_rows),
            "cutoff_date": cutoff_date,
        }

    # Boundary baseline preservation:
    # Identify active positions right before cutoff_date and ensure they are present at cutoff_date
    baseline_added = 0
    if should_preserve and archived_rows:
        # Group archived rows by ticker to find latest row before cutoff
        latest_archived_per_ticker: dict[str, dict[str, str]] = {}
        for r in archived_rows:
            t = r["ticker"]
            if t not in latest_archived_per_ticker or r["date"] > latest_archived_per_ticker[t]["date"]:
                latest_archived_per_ticker[t] = r

        existing_cutoff_tickers = {r["ticker"] for r in retained_rows if r["date"] == cutoff_date}

        for ticker, last_state in latest_archived_per_ticker.items():
            try:
                qty = float(last_state.get("quantity") or 0)
            except ValueError:
                qty = 0.0
            try:
                val = float(last_state.get("value_pln") or 0)
            except ValueError:
                val = 0.0

            # Only preserve active holdings with non-zero quantity or value
            if (qty > 0 or val > 0) and ticker not in existing_cutoff_tickers:
                baseline_row = dict(last_state)
                baseline_row["date"] = cutoff_date
                retained_rows.append(baseline_row)
                baseline_added += 1

    # Group archived rows by calendar year YYYY
    archived_by_year: dict[str, list[dict[str, str]]] = {}
    for r in archived_rows:
        year = r["date"][:4]
        archived_by_year.setdefault(year, []).append(r)

    yearly_counts: dict[str, int] = {}
    if not dry_run:
        os.makedirs(archive_dir, exist_ok=True)

    for year, y_rows in sorted(archived_by_year.items()):
        archive_file = os.path.join(archive_dir, f"history-archive-{year}.csv")
        existing_archive_entries: dict[tuple[str, str], dict[str, str]] = {}

        if os.path.exists(archive_file):
            with open(archive_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    d, t = (r.get("date") or "").strip(), (r.get("ticker") or "").strip()
                    if d and t:
                        existing_archive_entries[(d, t)] = {k: (r.get(k) or "").strip() for k in PORTFOLIO_FIELDS}

        # Merge with incoming archived rows
        for r in y_rows:
            existing_archive_entries[(r["date"], r["ticker"])] = r

        merged_archive = sorted(list(existing_archive_entries.values()), key=lambda x: (x["date"], x["ticker"]))
        yearly_counts[year] = len(merged_archive)

        if not dry_run:
            with open(archive_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS, lineterminator="\n")
                writer.writeheader()
                writer.writerows(merged_archive)

    # Deduplicate and sort retained rows
    retained_map: dict[tuple[str, str], dict[str, str]] = {}
    for r in retained_rows:
        retained_map[(r["date"], r["ticker"])] = r

    final_retained = sorted(list(retained_map.values()), key=lambda x: (x["date"], x["ticker"]))

    if not dry_run:
        with open(portfolio_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(final_retained)

    logger.info(
        f"{'[DRY-RUN] ' if dry_run else ''}Archived {len(archived_rows)} entries older than {cutoff_date} "
        f"across years {list(archived_by_year.keys())}. Retained {len(final_retained)} entries "
        f"(baseline preserved: {baseline_added})."
    )

    return {
        "status": "archived",
        "archived_count": len(archived_rows),
        "retained_count": len(final_retained),
        "cutoff_date": cutoff_date,
        "yearly_archives": yearly_counts,
        "baseline_preserved_count": baseline_added,
        "dry_run": dry_run,
    }


def is_path_excluded(rel_path: str, exclude_patterns: list[str]) -> bool:
    """Check if a relative path matches any exclusion patterns."""
    normalized = rel_path.replace("\\", "/")
    parts = normalized.split("/")
    filename = parts[-1]

    # Exclude system and sample files
    for pat in exclude_patterns:
        norm_pat = pat.replace("\\", "/")
        # Match against filename directly
        if fnmatch.fnmatch(filename.lower(), norm_pat.lower()):
            return True
        # Match against full relative path
        if fnmatch.fnmatch(normalized.lower(), norm_pat.lower()):
            return True
        # Match against directory components
        for part in parts:
            if fnmatch.fnmatch(part.lower(), norm_pat.lower()):
                return True

    return False


def rotate_raw_data(
    base_dir: str | None = None,
    retention_days: int | None = None,
    action: str | None = None,
    dry_run: bool = False,
    compress_zip: bool | None = None,
) -> dict[str, Any]:
    """Rotate ephemeral raw broker exports in 00_Raw older than retention_days.

    Supports action='archive' (move to 00_Raw/archive/<platform>/ with collision safety)
    or action='prune' (permanent delete).
    """
    if base_dir is None:
        base_dir = get_base_dir()

    vault_cfg = load_vault_config(base_dir=base_dir)
    cfg: RawDataRetentionConfig = vault_cfg.retention.raw_data

    if not cfg.enabled:
        logger.info("Raw data retention is disabled in config.yaml.")
        return {"status": "disabled", "scanned_files": 0, "rotated_files": 0}

    days = retention_days if retention_days is not None else cfg.retention_days
    act = (action if action is not None else cfg.action).lower()
    zip_toggle = compress_zip if compress_zip is not None else cfg.compress_zip

    raw_dir = os.path.join(base_dir, "00_Raw")
    if not os.path.exists(raw_dir):
        return {"status": "not_found", "scanned_files": 0, "rotated_files": 0}

    archive_base_dir = os.path.join(base_dir, cfg.archive_dir)
    cutoff_dt = datetime.now() - timedelta(days=days)

    scanned = 0
    rotated: list[dict[str, Any]] = []

    for root, _, files in os.walk(raw_dir):
        for fname in files:
            file_path = os.path.join(root, fname)
            rel_path = os.path.relpath(file_path, raw_dir)

            # Check exclusion patterns
            if is_path_excluded(rel_path, cfg.exclude_patterns):
                continue

            scanned += 1

            # Determine file date (filename pattern first, fallback to mtime)
            file_dt = extract_date_from_filename(fname)
            if file_dt is None:
                mtime = os.path.getmtime(file_path)
                file_dt = datetime.fromtimestamp(mtime)

            if file_dt < cutoff_dt:
                age_days = (datetime.now() - file_dt).days
                rel_parts = rel_path.replace("\\", "/").split("/")
                platform = rel_parts[0] if len(rel_parts) > 1 else "misc"

                file_info = {
                    "file": rel_path,
                    "platform": platform,
                    "file_date": file_dt.strftime("%Y-%m-%d"),
                    "age_days": age_days,
                    "action": act,
                }

                if act == "prune":
                    if not dry_run:
                        os.remove(file_path)
                    rotated.append(file_info)

                elif act == "archive":
                    dest_dir = os.path.join(archive_base_dir, platform)
                    dest_path = os.path.join(dest_dir, fname)

                    if not dry_run:
                        os.makedirs(dest_dir, exist_ok=True)

                    if os.path.exists(dest_path):
                        # Collision resolution: compare checksum
                        if compute_file_sha256(file_path) == compute_file_sha256(dest_path):
                            # Identical file already archived, remove source
                            if not dry_run:
                                os.remove(file_path)
                            file_info["collision"] = "identical_deduplicated"
                        else:
                            # Content differs: disambiguate with timestamp
                            stem, ext = os.path.splitext(fname)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            dest_path = os.path.join(dest_dir, f"{stem}_{ts}{ext}")
                            if not dry_run:
                                shutil.move(file_path, dest_path)
                            file_info["collision"] = "renamed_with_timestamp"
                    else:
                        if not dry_run:
                            shutil.move(file_path, dest_path)

                    file_info["destination"] = os.path.relpath(dest_path, base_dir)

                    if zip_toggle and not dry_run and os.path.exists(dest_path):
                        zip_file_path = os.path.join(dest_dir, f"{platform}.zip")
                        with zipfile.ZipFile(zip_file_path, "a", zipfile.ZIP_DEFLATED) as zf:
                            zf.write(dest_path, arcname=os.path.basename(dest_path))
                        os.remove(dest_path)
                        file_info["destination"] = os.path.relpath(zip_file_path, base_dir)

                    rotated.append(file_info)

    logger.info(
        f"{'[DRY-RUN] ' if dry_run else ''}Scanned {scanned} raw files. "
        f"Rotated {len(rotated)} expired files (> {days} days) via '{act}'."
    )

    return {
        "status": "ok",
        "scanned_files": scanned,
        "rotated_count": len(rotated),
        "action": act,
        "rotated_files": rotated,
        "dry_run": dry_run,
    }


def run_retention_pipeline(
    base_dir: str | None = None,
    dry_run: bool = False,
    history_only: bool = False,
    raw_only: bool = False,
) -> dict[str, Any]:
    """Execute both portfolio history archival and raw data rotation."""
    if base_dir is None:
        base_dir = get_base_dir()

    results: dict[str, Any] = {}

    if not raw_only:
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Running portfolio history archival...")
        results["history"] = archive_portfolio_history(base_dir=base_dir, dry_run=dry_run)

    if not history_only:
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Running ephemeral raw data rotation...")
        results["raw_data"] = rotate_raw_data(base_dir=base_dir, dry_run=dry_run)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Data Retention & History Archival CLI runner.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate archival and rotation without modifying files on disk.",
    )
    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Only archive historical portfolio.csv records.",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Only rotate ephemeral raw broker exports in 00_Raw.",
    )
    parser.add_argument(
        "--retention-days-history",
        type=int,
        default=None,
        help="Override days threshold for history archival (default from config.yaml: 730).",
    )
    parser.add_argument(
        "--retention-days-raw",
        type=int,
        default=None,
        help="Override days threshold for raw data rotation (default from config.yaml: 365).",
    )
    parser.add_argument(
        "--action",
        choices=["archive", "prune"],
        default=None,
        help="Override rotation action for raw data ('archive' or 'prune').",
    )

    args = parser.parse_args()
    base_dir = get_base_dir()

    if args.history_only and not args.raw_only:
        res = archive_portfolio_history(
            base_dir=base_dir,
            retention_days=args.retention_days_history,
            dry_run=args.dry_run,
        )
        print(f"History archival result: {res}")
    elif args.raw_only and not args.history_only:
        res = rotate_raw_data(
            base_dir=base_dir,
            retention_days=args.retention_days_raw,
            action=args.action,
            dry_run=args.dry_run,
        )
        print(f"Raw data rotation result: {res}")
    else:
        res = run_retention_pipeline(
            base_dir=base_dir,
            dry_run=args.dry_run,
            history_only=args.history_only,
            raw_only=args.raw_only,
        )
        print(f"Retention pipeline result: {res}")


if __name__ == "__main__":
    main()
