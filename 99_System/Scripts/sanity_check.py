"""Vault Sanity & Data Integrity Checker.

Performs comprehensive validation across:
1. Frontmatter validation for all notes in 10_Finance/Assets/*.md (required fields, numeric sanity, portfolio rules, collisions).
2. Historical timeline integrity in 10_Finance/History/portfolio.csv (schema, date monotonicity, duplicate snapshots, --fix mode).
3. Raw broker exports validation in 00_Raw/ (supported file types, corrupt/unparseable files, empty exports).
4. Environment configuration verification (.env presence, syntax, placeholder values).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

# Encoding helpers for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

CANONICAL_PORTFOLIOS = {"safety net", "safety", "long term", "long_term", "aggressive"}


@dataclass
class SanityIssue:
    """Represents an identified sanity or integrity issue."""

    category: str  # "Assets", "History", "Raw Exports", "Environment"
    severity: Literal["ERROR", "WARN", "INFO"]
    file_path: str
    message: str
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "file_path": self.file_path,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class SanityReport:
    """Aggregated validation report."""

    target_vault: str
    issues: list[SanityIssue] = field(default_factory=list)
    probed_assets_count: int = 0
    probed_history_rows_count: int = 0
    probed_raw_files_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARN")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "INFO")

    @property
    def is_clean(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_vault": self.target_vault,
            "is_clean": self.is_clean,
            "error_count": self.error_count,
            "warn_count": self.warn_count,
            "info_count": self.info_count,
            "probed_assets_count": self.probed_assets_count,
            "probed_history_rows_count": self.probed_history_rows_count,
            "probed_raw_files_count": self.probed_raw_files_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ==============================================================================
# 1. Frontmatter Validation (10_Finance/Assets/*.md)
# ==============================================================================


def _extract_frontmatter(content: str) -> dict[str, Any] | None:
    """Extract and parse YAML frontmatter from note text."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        import yaml

        data = yaml.safe_load(parts[1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def probe_assets(vault_path: str) -> tuple[list[SanityIssue], int]:
    """Validate all markdown asset notes in 10_Finance/Assets."""
    issues: list[SanityIssue] = []
    assets_dir = os.path.join(vault_path, "10_Finance", "Assets")
    if not os.path.exists(assets_dir):
        issues.append(
            SanityIssue(
                category="Assets",
                severity="WARN",
                file_path="10_Finance/Assets",
                message="Assets directory does not exist.",
            )
        )
        return issues, 0

    # Collision detection map: (ticker_upper, platform_lower) -> list of file_paths
    seen_assets: dict[tuple[str, str], list[str]] = {}
    probed_count = 0

    for fname in sorted(os.listdir(assets_dir)):
        if not fname.endswith(".md"):
            continue
        probed_count += 1
        fpath = os.path.join(assets_dir, fname)
        rel_path = os.path.join("10_Finance", "Assets", fname)

        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            issues.append(
                SanityIssue(
                    category="Assets",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Failed to read asset note: {e}",
                )
            )
            continue

        fm = _extract_frontmatter(content)
        if fm is None:
            issues.append(
                SanityIssue(
                    category="Assets",
                    severity="ERROR",
                    file_path=rel_path,
                    message="Missing or unparseable YAML frontmatter header (must start with '---').",
                )
            )
            continue

        # 1. Required: ticker
        ticker = fm.get("ticker")
        if not ticker or not isinstance(ticker, str) or not ticker.strip():
            issues.append(
                SanityIssue(
                    category="Assets",
                    severity="ERROR",
                    file_path=rel_path,
                    message="Missing or empty required field: 'ticker'.",
                )
            )
            ticker_str = ""
        else:
            ticker_str = ticker.strip()

        # 2. Required: platform
        platform = fm.get("platform")
        platform_str = str(platform).strip() if platform is not None else ""

        # Collision detection (ticker, platform)
        if ticker_str and platform_str:
            key = (ticker_str.upper(), platform_str.lower())
            if key in seen_assets:
                seen_assets[key].append(rel_path)
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Ticker collision detected: '{ticker_str}' on platform '{platform_str}'.",
                        details=f"Already defined in: {', '.join(seen_assets[key][:-1])}",
                    )
                )
            else:
                seen_assets[key] = [rel_path]

        # 3. Required: currency
        currency = fm.get("currency")
        if not currency or not isinstance(currency, str) or not currency.strip():
            issues.append(
                SanityIssue(
                    category="Assets",
                    severity="ERROR",
                    file_path=rel_path,
                    message="Missing or invalid required field: 'currency'.",
                )
            )

        # 4. Required & Numeric Sanity: value_base (with value_pln compatibility)
        val_base = fm.get("value_base")
        if val_base is None:
            val_base = fm.get("value_pln")
            if val_base is None:
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message="Missing required field: 'value_base'.",
                    )
                )
            else:
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="WARN",
                        file_path=rel_path,
                        message="Missing 'value_base' field (falling back to legacy 'value_pln').",
                    )
                )

        if val_base is not None:
            try:
                num_val = float(val_base)
                if math.isnan(num_val) or math.isinf(num_val):
                    issues.append(
                        SanityIssue(
                            category="Assets",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Invalid numeric value for 'value_base': {val_base} (NaN/Infinity).",
                        )
                    )
                elif num_val < 0:
                    issues.append(
                        SanityIssue(
                            category="Assets",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Negative 'value_base' detected: {num_val}.",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Non-numeric 'value_base' value: {val_base}.",
                    )
                )

        # 5. Numeric Sanity: quantity
        qty = fm.get("quantity")
        asset_type = str(fm.get("asset_type") or "").strip().lower()
        if qty is None:
            issues.append(
                SanityIssue(
                    category="Assets",
                    severity="ERROR",
                    file_path=rel_path,
                    message="Missing required field: 'quantity'.",
                )
            )
        else:
            try:
                num_qty = float(qty)
                if math.isnan(num_qty) or math.isinf(num_qty):
                    issues.append(
                        SanityIssue(
                            category="Assets",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Invalid numeric value for 'quantity': {qty} (NaN/Infinity).",
                        )
                    )
                elif num_qty < 0:
                    issues.append(
                        SanityIssue(
                            category="Assets",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Negative position quantity detected: {num_qty}.",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Non-numeric 'quantity' value: {qty}.",
                    )
                )

        # 6. Portfolio Silo rule validation
        portfolio = fm.get("portfolio")
        if portfolio is None or portfolio == "" or str(portfolio).lower() in ("null", "none"):
            # Cash assets are allowed to have portfolio: null (unallocated dry powder)
            if asset_type != "cash":
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message="Missing required 'portfolio' allocation for invested asset.",
                        details="Must be one of: 'Safety net', 'Long term', or 'Aggressive'.",
                    )
                )
        else:
            norm_port = str(portfolio).strip().lower().replace("_", " ")
            if norm_port not in ("safety net", "safety", "long term", "aggressive"):
                issues.append(
                    SanityIssue(
                        category="Assets",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Invalid portfolio bucket: '{portfolio}'.",
                        details="Must be one of: 'Safety net', 'Long term', or 'Aggressive'.",
                    )
                )

    return issues, probed_count


# ==============================================================================
# 2. Historical Timeline Validation (10_Finance/History/portfolio.csv)
# ==============================================================================

REQUIRED_HISTORY_COLUMNS = ["date", "ticker"]


def probe_history(vault_path: str, fix: bool = False) -> tuple[list[SanityIssue], int]:
    """Validate schema, monotonicity, and duplicates in portfolio.csv. Fix if requested."""
    issues: list[SanityIssue] = []
    history_file = os.path.join(vault_path, "10_Finance", "History", "portfolio.csv")
    rel_path = os.path.join("10_Finance", "History", "portfolio.csv")

    if not os.path.exists(history_file):
        issues.append(
            SanityIssue(
                category="History",
                severity="WARN",
                file_path=rel_path,
                message="Historical timeline file 'portfolio.csv' does not exist yet.",
                details="Will be generated automatically when running 'python run.py --history'.",
            )
        )
        return issues, 0

    rows: list[dict[str, str]] = []
    headers: list[str] = []

    try:
        with open(history_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header_row = next(reader, None)
            if not header_row:
                issues.append(
                    SanityIssue(
                        category="History",
                        severity="ERROR",
                        file_path=rel_path,
                        message="History file is empty (missing CSV header row).",
                    )
                )
                return issues, 0
            headers = [h.strip() for h in header_row]
            for line_idx, r in enumerate(reader, start=2):
                if not r or not any(field.strip() for field in r):
                    continue
                if len(r) != len(headers):
                    issues.append(
                        SanityIssue(
                            category="History",
                            severity="WARN",
                            file_path=rel_path,
                            message=f"Line {line_idx} column count mismatch: expected {len(headers)}, got {len(r)}.",
                        )
                    )
                # Zip into dict using headers
                row_dict = {headers[i]: r[i] if i < len(r) else "" for i in range(len(headers))}
                rows.append(row_dict)
    except Exception as e:
        issues.append(
            SanityIssue(
                category="History",
                severity="ERROR",
                file_path=rel_path,
                message=f"Failed to parse CSV file: {e}",
            )
        )
        return issues, 0

    # 1. Header validation
    for req_col in REQUIRED_HISTORY_COLUMNS:
        if req_col not in headers:
            issues.append(
                SanityIssue(
                    category="History",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Missing required CSV column header: '{req_col}'.",
                )
            )

    if "value_base" not in headers and "value_pln" not in headers:
        issues.append(
            SanityIssue(
                category="History",
                severity="ERROR",
                file_path=rel_path,
                message="Missing required CSV column header: 'value_base'.",
            )
        )

    # 2. Monotonicity & Duplicate checks
    prev_date: str | None = None
    seen_snapshots: set[tuple[str, str]] = set()
    has_monotonicity_issue = False
    has_duplicates_issue = False

    for idx, row in enumerate(rows, start=2):
        row_date = row.get("date", "").strip()
        row_ticker = row.get("ticker", "").strip()

        # Validate date format (YYYY-MM-DD)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", row_date):
            issues.append(
                SanityIssue(
                    category="History",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Line {idx}: Invalid date format '{row_date}'. Expected 'YYYY-MM-DD'.",
                )
            )
            continue

        # Monotonicity: dates should be non-decreasing
        if prev_date and row_date < prev_date:
            has_monotonicity_issue = True
            issues.append(
                SanityIssue(
                    category="History",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Line {idx}: Non-chronological date sequence ({row_date} appears after {prev_date}).",
                )
            )
        prev_date = row_date

        # Duplicates: duplicate (date, ticker)
        snapshot_key = (row_date, row_ticker)
        if snapshot_key in seen_snapshots:
            has_duplicates_issue = True
            issues.append(
                SanityIssue(
                    category="History",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Line {idx}: Duplicate snapshot for ticker '{row_ticker}' on date '{row_date}'.",
                )
            )
        else:
            seen_snapshots.add(snapshot_key)

        # Numeric validation for value_base (with value_pln compatibility)
        val_str = (row.get("value_base") or row.get("value_pln") or "").strip()
        if val_str:
            try:
                float(val_str)
            except ValueError:
                issues.append(
                    SanityIssue(
                        category="History",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Line {idx}: Non-numeric 'value_base' value: '{val_str}'.",
                    )
                )

    # 3. Optional Auto-Fix Mode
    if fix and (has_monotonicity_issue or has_duplicates_issue) and rows:
        try:
            # Create backup
            backup_file = history_file + ".bak"
            shutil.copy2(history_file, backup_file)

            # Sort chronologically by date and ticker
            sorted_rows = sorted(rows, key=lambda row_val: (row_val.get("date", ""), row_val.get("ticker", "")))

            # Deduplicate keeping last occurrence
            deduped_rows: list[dict[str, str]] = []
            seen_fix_keys: set[tuple[str, str]] = set()

            for item in reversed(sorted_rows):
                k = (item.get("date", "").strip(), item.get("ticker", "").strip())
                if k not in seen_fix_keys:
                    seen_fix_keys.add(k)
                    deduped_rows.append(item)
            deduped_rows.reverse()

            # Write fixed CSV
            with open(history_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(deduped_rows)

            issues.append(
                SanityIssue(
                    category="History",
                    severity="INFO",
                    file_path=rel_path,
                    message=f"Auto-fix applied: Sorted and deduplicated {len(deduped_rows)} rows (Backup created: portfolio.csv.bak).",
                )
            )
        except Exception as e:
            issues.append(
                SanityIssue(
                    category="History",
                    severity="ERROR",
                    file_path=rel_path,
                    message=f"Failed to auto-fix portfolio.csv: {e}",
                )
            )

    return issues, len(rows)


# ==============================================================================
# 3. Raw Broker Exports Validation (00_Raw/)
# ==============================================================================

VALID_RAW_EXTENSIONS = {".csv", ".xls", ".xlsx", ".txt", ".md", ".gitkeep"}
SUSPICIOUS_RAW_EXTENSIONS = {".exe", ".zip", ".tar", ".gz", ".tmp", ".bak", ".bad", ".bin"}


def probe_raw_exports(vault_path: str) -> tuple[list[SanityIssue], int]:
    """Validate file types and readability of raw broker data in 00_Raw/."""
    issues: list[SanityIssue] = []
    raw_dir = os.path.join(vault_path, "00_Raw")
    if not os.path.exists(raw_dir):
        issues.append(
            SanityIssue(
                category="Raw Exports",
                severity="WARN",
                file_path="00_Raw",
                message="Raw broker data directory '00_Raw/' does not exist.",
            )
        )
        return issues, 0

    probed_count = 0

    for root, dirs, files in os.walk(raw_dir):
        # Exclude historical archives
        dirs[:] = [d for d in dirs if d != "archive"]

        for fname in files:
            probed_count += 1
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, vault_path)
            _, ext = os.path.splitext(fname)
            ext_lower = ext.lower()

            # 1. Check extension validity
            if ext_lower in SUSPICIOUS_RAW_EXTENSIONS:
                issues.append(
                    SanityIssue(
                        category="Raw Exports",
                        severity="ERROR",
                        file_path=rel_path,
                        message=f"Unsupported / suspicious file format in raw export directory: '{fname}'.",
                    )
                )
                continue
            elif ext_lower and ext_lower not in VALID_RAW_EXTENSIONS:
                issues.append(
                    SanityIssue(
                        category="Raw Exports",
                        severity="WARN",
                        file_path=rel_path,
                        message=f"Unrecognized file extension '{ext_lower}'. Supported formats are CSV, Excel, TXT.",
                    )
                )

            # 2. Check for empty files (except .gitkeep)
            file_size = os.path.getsize(fpath)
            if file_size == 0 and fname != ".gitkeep":
                issues.append(
                    SanityIssue(
                        category="Raw Exports",
                        severity="WARN",
                        file_path=rel_path,
                        message=f"Zero-byte empty file detected: '{fname}'.",
                    )
                )
                continue

            # 3. Readability & corruption checks
            if ext_lower == ".csv" and file_size > 0:
                try:
                    # Test if readable with common encodings
                    decoded = False
                    for enc in ("utf-8", "utf-16", "cp1250", "latin1"):
                        try:
                            with open(fpath, encoding=enc) as f:
                                f.read(512)
                            decoded = True
                            break
                        except Exception:
                            continue
                    if not decoded:
                        issues.append(
                            SanityIssue(
                                category="Raw Exports",
                                severity="ERROR",
                                file_path=rel_path,
                                message="Corrupt or binary unreadable CSV file (failed UTF-8, UTF-16, and CP1250 decoding).",
                            )
                        )
                except Exception as e:
                    issues.append(
                        SanityIssue(
                            category="Raw Exports",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Failed to read CSV export: {e}",
                        )
                    )

            elif ext_lower in (".xls", ".xlsx") and file_size > 0:
                # Basic signature check for Excel files
                try:
                    with open(fpath, "rb") as f:
                        header_bytes = f.read(8)
                    # OLE compound file for .xls: D0 CF 11 E0 A1 B1 1A E1
                    # Zip container for .xlsx: 50 4B 03 04
                    is_ole = header_bytes.startswith(b"\xd0\xcf\x11\xe0")
                    is_zip = header_bytes.startswith(b"\x50\x4b\x03\x04")
                    if ext_lower == ".xls" and not is_ole and not is_zip:
                        # Some brokers output HTML or CSV disguised as .xls
                        try:
                            with open(fpath, encoding="utf-8", errors="ignore") as f:
                                txt = f.read(200)
                            if "<html" in txt.lower() or "<table" in txt.lower():
                                issues.append(
                                    SanityIssue(
                                        category="Raw Exports",
                                        severity="WARN",
                                        file_path=rel_path,
                                        message="Excel file contains HTML table export instead of native binary format.",
                                    )
                                )
                            else:
                                issues.append(
                                    SanityIssue(
                                        category="Raw Exports",
                                        severity="WARN",
                                        file_path=rel_path,
                                        message="Non-standard header signature for .xls file.",
                                    )
                                )
                        except Exception:
                            pass
                except Exception as e:
                    issues.append(
                        SanityIssue(
                            category="Raw Exports",
                            severity="ERROR",
                            file_path=rel_path,
                            message=f"Failed to verify Excel header signature: {e}",
                        )
                    )

    return issues, probed_count


# ==============================================================================
# 4. Environment Verification (.env)
# ==============================================================================

KNOWN_ENV_KEYS = [
    "FINNHUB_API_KEY",
    "EXANTE_API_KEY",
    "EXANTE_API_SECRET",
    "EXANTE_ACCOUNT_ID",
    "EXANTE_API_URL",
]

PLACEHOLDER_MARKERS = [
    "your_api_key",
    "your_exante",
    "your_shared_key",
    "your_account",
    "your_application",
    "placeholder",
    "xxx",
]


def probe_environment(vault_path: str) -> list[SanityIssue]:
    """Verify presence, syntax, and validity of .env configuration."""
    issues: list[SanityIssue] = []
    env_file = os.path.join(vault_path, ".env")
    env_example = os.path.join(vault_path, ".env.example")

    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            issues.append(
                SanityIssue(
                    category="Environment",
                    severity="WARN",
                    file_path=".env",
                    message="Missing '.env' file. Configuration template '.env.example' is present.",
                    details="Run 'cp .env.example .env' and populate your broker API keys.",
                )
            )
        else:
            issues.append(
                SanityIssue(
                    category="Environment",
                    severity="ERROR",
                    file_path=".env",
                    message="Missing '.env' file and '.env.example' template not found.",
                )
            )
        return issues

    # Validate syntax and contents
    try:
        with open(env_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        issues.append(
            SanityIssue(
                category="Environment",
                severity="ERROR",
                file_path=".env",
                message=f"Failed to read '.env' file: {e}",
            )
        )
        return issues

    exante_api_active = False
    cfg_file = os.path.join(vault_path, "config.yaml")
    if os.path.exists(cfg_file):
        try:
            import yaml

            with open(cfg_file, encoding="utf-8") as f:
                raw_cfg_check = yaml.safe_load(f) or {}
            ex_cfg = (raw_cfg_check.get("platforms") or {}).get("exante") or {}
            if ex_cfg.get("enabled", True) and str(ex_cfg.get("default_mode", "csv")).strip().lower() == "api":
                exante_api_active = True
        except Exception:
            pass

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            issues.append(
                SanityIssue(
                    category="Environment",
                    severity="ERROR",
                    file_path=".env",
                    message=f"Line {line_no}: Invalid syntax in '.env' (missing '=' separator).",
                    details=f"Line content: '{line}'",
                )
            )
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")

        # Skip EXANTE_* placeholder warnings if Exante is disabled or configured for CSV mode
        if key.upper().startswith("EXANTE_") and not exante_api_active:
            continue

        # Check for placeholder values
        if any(marker in val.lower() for marker in PLACEHOLDER_MARKERS):
            issues.append(
                SanityIssue(
                    category="Environment",
                    severity="WARN",
                    file_path=".env",
                    message=f"Line {line_no}: '{key}' appears to contain a default placeholder value ('{val}').",
                )
            )

    # Validate config.yaml localization
    if os.path.exists(cfg_file):
        try:
            import yaml

            with open(cfg_file, encoding="utf-8") as f:
                raw_cfg = yaml.safe_load(f) or {}
            loc = raw_cfg.get("localization")
            if not loc:
                issues.append(
                    SanityIssue(
                        category="Environment",
                        severity="WARN",
                        file_path="config.yaml",
                        message="Missing 'localization' section in 'config.yaml'.",
                        details="Defaults to base_currency: 'PLN'.",
                    )
                )
            elif not loc.get("base_currency"):
                issues.append(
                    SanityIssue(
                        category="Environment",
                        severity="ERROR",
                        file_path="config.yaml",
                        message="Missing required 'base_currency' in localization config.",
                    )
                )
        except Exception as e:
            issues.append(
                SanityIssue(
                    category="Environment",
                    severity="ERROR",
                    file_path="config.yaml",
                    message=f"Failed to parse 'config.yaml': {e}",
                )
            )

    return issues


# ==============================================================================
# 5. Master Runner & Rich Reporting
# ==============================================================================


def run_sanity_check(
    vault_path: str | None = None,
    fix: bool = False,
    verbose: bool = False,
) -> tuple[SanityReport, int]:
    """Execute all sanity checks, display Rich terminal diagnostic report, and return exit code."""
    vault = os.path.abspath(vault_path or VAULT_ROOT)
    report = SanityReport(target_vault=vault)

    # 1. Assets probe
    asset_issues, asset_count = probe_assets(vault)
    report.issues.extend(asset_issues)
    report.probed_assets_count = asset_count

    # 2. History probe
    history_issues, history_count = probe_history(vault, fix=fix)
    report.issues.extend(history_issues)
    report.probed_history_rows_count = history_count

    # 3. Raw exports probe
    raw_issues, raw_count = probe_raw_exports(vault)
    report.issues.extend(raw_issues)
    report.probed_raw_files_count = raw_count

    # 4. Environment probe
    env_issues = probe_environment(vault)
    report.issues.extend(env_issues)

    # Render report to terminal
    _print_report(report, verbose=verbose, fix=fix)

    exit_code = 0 if report.is_clean else 1
    return report, exit_code


def _print_report(report: SanityReport, verbose: bool = False, fix: bool = False):
    """Render Rich visual terminal table or fallback plaintext."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        use_rich = True
    except ImportError:
        console = None
        use_rich = False

    title_str = "🔍  VAULT SANITY & DATA INTEGRITY DIAGNOSTICS"

    if use_rich and console:
        console.print()
        console.print(f"[bold cyan]{'=' * 72}[/bold cyan]")
        console.print(f"[bold cyan]{title_str}[/bold cyan]")
        console.print(f"[bold cyan]{'=' * 72}[/bold cyan]")
        console.print(f"📁 Target Vault : [bold]{report.target_vault}[/bold]")
        console.print(f"🕒 Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if fix:
            console.print("🔧 Mode         : [bold yellow][AUTO-FIX ACTIVE][/bold yellow]")
        console.print()

        # Probes summary table
        table = Table(title="📊 Integrity Probes Summary", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="bold", width=18)
        table.add_column("Inspected Entities", justify="right", width=20)
        table.add_column("Errors", justify="right", width=10)
        table.add_column("Warnings", justify="right", width=10)
        table.add_column("Status", width=12)

        categories = [
            ("Assets", f"{report.probed_assets_count} notes"),
            ("History", f"{report.probed_history_rows_count} rows"),
            ("Raw Exports", f"{report.probed_raw_files_count} files"),
            ("Environment", "1 .env file"),
        ]

        for cat, count_str in categories:
            cat_issues = [i for i in report.issues if i.category == cat]
            errs = sum(1 for i in cat_issues if i.severity == "ERROR")
            warns = sum(1 for i in cat_issues if i.severity == "WARN")

            if errs > 0:
                status = "[bold red]❌ FAIL[/bold red]"
            elif warns > 0:
                status = "[bold yellow]⚠️ WARN[/bold yellow]"
            else:
                status = "[bold green]✅ PASS[/bold green]"

            table.add_row(
                cat,
                count_str,
                f"[red]{errs}[/red]" if errs else "0",
                f"[yellow]{warns}[/yellow]" if warns else "0",
                status,
            )

        console.print(table)
        console.print()

        # Print detailed issues if any
        if report.issues:
            issues_table = Table(title="📋 Identified Integrity Issues", show_header=True, header_style="bold cyan")
            issues_table.add_column("Severity", width=10)
            issues_table.add_column("Category", width=14)
            issues_table.add_column("Target File", width=30)
            issues_table.add_column("Description", width=42)

            for issue in report.issues:
                if issue.severity == "ERROR":
                    sev_style = "[bold red]ERROR[/bold red]"
                elif issue.severity == "WARN":
                    sev_style = "[bold yellow]WARN[/bold yellow]"
                else:
                    sev_style = "[bold blue]INFO[/bold blue]"

                desc = issue.message
                if issue.details:
                    desc += f" [dim]({issue.details})[/dim]"

                issues_table.add_row(sev_style, issue.category, issue.file_path, desc)

            console.print(issues_table)
            console.print()

        # Final verdict banner
        if report.is_clean:
            if report.warn_count == 0:
                msg = "[bold green]✨ All vault integrity checks passed! Zero errors detected.[/bold green]"
            else:
                msg = (
                    f"[bold yellow]⚠️  All critical checks passed with {report.warn_count} warning(s). "
                    f"Core data integrity intact.[/bold yellow]"
                )
            console.print(Panel(msg, border_style="green" if report.warn_count == 0 else "yellow"))
        else:
            msg = (
                f"[bold red]❌ Vault sanity check failed with {report.error_count} error(s) "
                f"and {report.warn_count} warning(s). Review issues above.[/bold red]"
            )
            console.print(Panel(msg, border_style="red"))

    else:
        # Plaintext fallback
        print("=" * 72)
        print(title_str)
        print("=" * 72)
        print(f"Target Vault : {report.target_vault}")
        print(f"Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 72)
        print(
            f"Assets: {report.probed_assets_count} notes | History: {report.probed_history_rows_count} rows | "
            f"Raw Exports: {report.probed_raw_files_count} files"
        )
        print(f"Errors: {report.error_count} | Warnings: {report.warn_count}")
        print("-" * 72)

        for issue in report.issues:
            print(f"[{issue.severity}] [{issue.category}] {issue.file_path}: {issue.message}")
            if issue.details:
                print(f"       -> Details: {issue.details}")

        print("=" * 72)
        if report.is_clean:
            print("Status: ✅ PASS")
        else:
            print("Status: ❌ FAIL")
        print("=" * 72)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vault Sanity & Data Integrity Checker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        type=str,
        default=None,
        help="Target vault path (defaults to root of this vault).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt automated safe fixes for repairable issues (e.g. portfolio.csv sorting & deduplication).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed verbose issue descriptions.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON diagnostic report to stdout.",
    )

    args = parser.parse_args()

    report, exit_code = run_sanity_check(
        vault_path=args.target,
        fix=args.fix,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
