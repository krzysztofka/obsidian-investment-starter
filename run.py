#!/usr/bin/env python3
"""Unified CLI Runner for Investment Second Brain & Portfolio Management System.

Provides a unified command interface to execute portfolio pipeline actions:
  --import        : Import broker positions from Degiro / Exante CSV exports
  --update-rates  : Refresh currency FX rates to PLN and update asset valuations
  --macro         : Synchronize macroeconomic dashboard indicators, yields & rates
  --sync-etfs     : Synchronize ETF top holdings, overlap & exposures
  --alerts        : Scan and evaluate portfolio alerts (Alert Rules Engine)
  --history       : Synchronize portfolio historical timeline into portfolio.csv
  --all           : Execute all portfolio pipeline actions in logical sequence
"""

import os
import sys
import time
import argparse
from typing import Optional, List, Tuple, Dict, Any

# Configure UTF-8 encoding and line buffering for stdout/stderr on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

# Resolve vault root directory and ensure 99_System/Scripts is in sys.path
SCRIPT_PATH = os.path.abspath(__file__)
VAULT_ROOT = os.path.dirname(SCRIPT_PATH)
# If script is placed inside 99_System/Scripts, detect root accordingly
if os.path.basename(VAULT_ROOT) == "Scripts":
    VAULT_ROOT = os.path.abspath(os.path.join(VAULT_ROOT, "../.."))

SCRIPTS_DIR = os.path.join(VAULT_ROOT, "99_System", "Scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

LOG_FILE_PATH = os.path.join(VAULT_ROOT, "99_System", "runner.log")


class TeeLogger:
    """Tees output to terminal stream and a persistent runner.log file."""

    def __init__(self, stream, log_path: str):
        self.stream = stream
        self.log_path = log_path
        self._file = None
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            self._file = open(log_path, "a", encoding="utf-8", buffering=1)
        except Exception:
            pass

    def write(self, data):
        try:
            self.stream.write(data)
            self.stream.flush()
        except Exception:
            pass
        if self._file:
            try:
                self._file.write(data)
                self._file.flush()
            except Exception:
                pass

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass
        if self._file:
            try:
                self._file.flush()
            except Exception:
                pass

    def isatty(self):
        return getattr(self.stream, "isatty", lambda: False)()


# Enable output teeing to 99_System/runner.log
sys.stdout = TeeLogger(sys.stdout, LOG_FILE_PATH)
sys.stderr = TeeLogger(sys.stderr, LOG_FILE_PATH)


# ==============================================================================
# Pipeline Step Implementations
# ==============================================================================

def run_import_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute broker asset import."""
    from import_assets import import_assets

    from platforms.common import load_import_config

    platform = getattr(args, "platform", None)
    file_path = getattr(args, "file", None)
    use_api = getattr(args, "use_api", None)
    use_csv = getattr(args, "use_csv", False)
    account_id = getattr(args, "account_id", None)

    if use_csv:
        effective_use_api = False
    elif use_api:
        effective_use_api = True
    elif file_path:
        effective_use_api = False
    else:
        cfg = load_import_config(vault_root)
        effective_use_api = cfg.get("exante", {}).get("default_mode", "api").lower() == "api"

    print("📥 Starting broker positions import...")
    if file_path:
        print(f"   Target file: {file_path}")
    elif platform:
        print(f"   Target platform: {platform}")
    elif effective_use_api:
        print("   Target: Degiro (CSV), Exante (REST API) & mBM (IKE/IKZE CSV)")
    else:
        print("   Target: All supported platforms (Degiro, Exante & mBM CSV)")

    results = import_assets(
        platform=platform,
        file=file_path,
        base_dir=vault_root,
        use_api=effective_use_api,
        account_id=account_id,
    )
    total_imported = sum(results.values()) if isinstance(results, dict) else 0
    print(f"   Import completed. Total positions processed: {total_imported}")
    return {"status": "ok", "details": results, "count": total_imported}


def run_update_rates_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute currency FX rates update and PLN valuation calculation."""
    from update_currencies import update_currencies

    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    print(f"💱 Updating live FX rates and PLN values in: {assets_dir}...")
    update_currencies(assets_dir)
    return {"status": "ok"}


def run_macro_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute macroeconomic dashboard synchronization."""
    from sync_macro import sync_macro

    macro_path = os.path.join(vault_root, "10_Finance", "Macro.md")
    dry_run = getattr(args, "dry_run", False)

    print("🌐 Synchronizing macroeconomic indicators, yields & rates...")
    if dry_run:
        print("   Mode: DRY-RUN (no files will be saved)")

    result = sync_macro(macro_path=macro_path, dry_run=dry_run)
    return {"status": "ok", "details": result}


def run_sync_etfs_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute ETF top holdings and cross-exposure synchronization."""
    from sync_etf_holdings import sync_all_etfs

    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    holdings_dir = os.path.join(vault_root, "10_Finance", "ETF_Holdings")
    target_etf = getattr(args, "etf", None)
    limit = getattr(args, "limit", None)
    dry_run = getattr(args, "dry_run", False)

    print("📊 Synchronizing ETF top holdings and exposure analytics...")
    if target_etf:
        print(f"   Target ETF: {target_etf}")
    if limit:
        print(f"   Holdings limit per ETF: {limit}")
    if dry_run:
        print("   Mode: DRY-RUN (simulated)")

    sync_all_etfs(
        assets_dir=assets_dir,
        holdings_dir=holdings_dir,
        target_etf=target_etf,
        limit=limit,
        dry_run=dry_run,
    )
    return {"status": "ok"}


def run_alerts_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute Alert Rules Engine scan."""
    from alerts.engine import AlertEngine

    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    rule_filter = getattr(args, "rule", None)
    dry_run = getattr(args, "dry_run", False)

    print("⚠️  Evaluating portfolio risk and valuation alerts...")
    if rule_filter:
        print(f"   Rule filter: {rule_filter}")
    if dry_run:
        print("   Mode: DRY-RUN (no files will be saved)")

    engine = AlertEngine()
    result = engine.run(
        assets_dir=assets_dir,
        save=not dry_run,
        rule_filter=rule_filter,
    )

    scanned = result.get("scanned", 0)
    updated = result.get("updated", 0)
    active_alerts = sum(result.get("alerts_by_type", {}).values())
    print(f"   Scanned {scanned} assets. Active alert flags: {active_alerts}. Modified files: {updated}")
    return {"status": "ok", "scanned": scanned, "updated": updated, "active_alerts": active_alerts}


def run_history_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute portfolio historical snapshot synchronization."""
    from history.update_portfolio import update_portfolio_history

    print("📜 Synchronizing portfolio history timeline into portfolio.csv...")
    csv_file = update_portfolio_history(base_dir=vault_root)
    print(f"   History synchronized at: {csv_file}")
    return {"status": "ok", "file": csv_file}


def run_export_template_step(args: argparse.Namespace, vault_root: str) -> Dict[str, Any]:
    """Execute clean template repository export."""
    from export_template import export_template

    target_dir = getattr(args, "target_dir", None)
    exported_path = export_template(target_dir=target_dir)
    return {"status": "ok", "target_dir": exported_path}


# ==============================================================================
# Pipeline Registry & Runner
# ==============================================================================

PIPELINE_STEPS = [
    ("import", "Import broker exports", run_import_step),
    ("update_rates", "Update currency FX rates & PLN values", run_update_rates_step),
    ("macro", "Synchronize macroeconomic indicators & yields", run_macro_step),
    ("sync_etfs", "Synchronize ETF top holdings & cross-exposure", run_sync_etfs_step),
    ("alerts", "Scan & evaluate portfolio alerts", run_alerts_step),
    ("history", "Synchronize portfolio historical timeline", run_history_step),
    ("export_template", "Export clean template repository", run_export_template_step),
]


def print_banner(vault_root: str):
    print("=" * 72)
    print("🚀  INVESTMENT SECOND BRAIN — UNIFIED RUNNER")
    print("=" * 72)
    print(f"📁 Vault Root : {vault_root}")
    print(f"🕒 Timestamp  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)
    print()


def print_summary(results: List[Tuple[str, str, str, float]]):
    print()
    print("=" * 72)
    print("📋  EXECUTION SUMMARY REPORT")
    print("=" * 72)
    header = f"{'Step':<16} | {'Description':<38} | {'Status':<10} | {'Duration'}"
    print(header)
    print("-" * 72)

    total_duration = 0.0
    all_success = True

    for step_id, description, status, duration in results:
        total_duration += duration
        if status == "SUCCESS":
            status_str = "✅ SUCCESS"
        elif status == "FAILED":
            status_str = "❌ FAILED"
            all_success = False
        else:
            status_str = "⏭️ SKIPPED"

        dur_str = f"{duration:.2f}s"
        print(f"{step_id:<16} | {description[:38]:<38} | {status_str:<10} | {dur_str}")

    print("-" * 72)
    print(f"Total Duration : {total_duration:.2f}s")
    if all_success:
        print("Status         : ✨ All requested actions completed successfully!")
    else:
        print("Status         : ⚠️  One or more actions failed. Check logs above.")
    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified CLI runner for Investment Second Brain & Portfolio Management System.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python run.py --all                      Run full pipeline (import -> rates -> etfs -> alerts -> history)
  python run.py --import                   Import broker CSV files for all platforms
  python run.py --import --platform degiro Import only Degiro positions
  python run.py --update-rates             Update FX rates and recalculate PLN values
  python run.py --sync-etfs                Sync ETF top holdings and exposures
  python run.py --sync-etfs --dry-run      Simulate ETF sync without writing files
  python run.py --alerts                   Scan and evaluate portfolio alert rules
  python run.py --alerts --rule overvalued Scan only overvalued alerts
  python run.py --history                  Update historical portfolio.csv snapshots
  python run.py --update-rates --alerts    Chain multiple actions in one run
""",
    )

    # Core action flags (from todo.md: --import, --update-rates, --sync-etfs, --alerts, --history)
    actions_group = parser.add_argument_group("primary actions")
    actions_group.add_argument(
        "--all",
        action="store_true",
        help="Run all pipeline actions in canonical sequence.",
    )
    actions_group.add_argument(
        "-i", "--import",
        dest="action_import",
        action="store_true",
        help="Import broker positions from Degiro / Exante / mBM CSV exports or REST API.",
    )
    actions_group.add_argument(
        "-r", "--update-rates", "--rates",
        dest="action_update_rates",
        action="store_true",
        help="Refresh currency FX rates to PLN and update asset valuations.",
    )
    actions_group.add_argument(
        "-m", "--macro", "--sync-macro",
        dest="action_macro",
        action="store_true",
        help="Synchronize macroeconomic indicators, Treasury yields, and rates to Macro.md.",
    )
    actions_group.add_argument(
        "-s", "--sync-etfs",
        dest="action_sync_etfs",
        action="store_true",
        help="Synchronize ETF top holdings, overlap & exposures.",
    )
    actions_group.add_argument(
        "-a", "--alerts",
        dest="action_alerts",
        action="store_true",
        help="Scan and evaluate portfolio alerts (Alert Rules Engine).",
    )
    actions_group.add_argument(
        "-H", "--history",
        dest="action_history",
        action="store_true",
        help="Synchronize portfolio historical timeline into portfolio.csv.",
    )
    actions_group.add_argument(
        "--export-template",
        dest="action_export_template",
        action="store_true",
        help="Export clean template repository to ../obsidian-investment-template.",
    )

    # Step-specific fine-tuning options
    step_opts = parser.add_argument_group("action options")
    step_opts.add_argument(
        "-p", "--platform",
        type=str,
        default=None,
        help="[--import] Broker platform (e.g., 'degiro', 'exante', 'mbm', 'ike', 'ikze'). Default: all.",
    )
    step_opts.add_argument(
        "-f", "--file",
        type=str,
        default=None,
        help="[--import] Path to specific broker CSV file.",
    )
    step_opts.add_argument(
        "--api",
        dest="use_api",
        action="store_true",
        default=None,
        help="[--import] Force Exante REST API import mode (overrides config.yaml default_mode).",
    )
    step_opts.add_argument(
        "--csv",
        dest="use_csv",
        action="store_true",
        default=False,
        help="[--import] Force Exante CSV export import mode (overrides config.yaml default_mode).",
    )
    step_opts.add_argument(
        "--account",
        dest="account_id",
        type=str,
        default=None,
        help="[--import] Exante account ID for API import (optional, auto-detected if omitted).",
    )
    step_opts.add_argument(
        "--etf",
        type=str,
        default=None,
        help="[--sync-etfs] Specific ETF ticker/ISIN to synchronize.",
    )
    step_opts.add_argument(
        "--limit",
        type=int,
        default=None,
        help="[--sync-etfs] Maximum number of top holdings to fetch per ETF.",
    )
    step_opts.add_argument(
        "--rule",
        type=str,
        default=None,
        help="[--alerts] Filter specific alert rule (e.g., 'overvalued', 'stop_loss').",
    )
    step_opts.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="[--export-template] Target directory for exported template repository.",
    )

    # Global runtime options
    global_opts = parser.add_argument_group("global options")
    global_opts.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate run without writing file modifications (alerts, macro, and sync-etfs).",
    )
    global_opts.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately if any pipeline step fails.",
    )
    global_opts.add_argument(
        "--base-dir",
        type=str,
        default=None,
        help="Custom root directory path for the vault.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Determine vault root
    vault_root = os.path.abspath(args.base_dir) if args.base_dir else VAULT_ROOT

    # Determine requested actions
    requested_steps = []
    run_all = args.all

    if run_all or args.action_import:
        requested_steps.append("import")
    if run_all or args.action_update_rates:
        requested_steps.append("update_rates")
    if run_all or args.action_macro:
        requested_steps.append("macro")
    if run_all or args.action_sync_etfs:
        requested_steps.append("sync_etfs")
    if run_all or args.action_alerts:
        requested_steps.append("alerts")
    if run_all or args.action_history:
        requested_steps.append("history")
    if args.action_export_template:
        requested_steps.append("export_template")

    # If no action is specified, print help and exit cleanly
    if not requested_steps:
        print_banner(vault_root)
        parser.print_help()
        print("\n💡 Tip: Run 'python run.py --all' to execute the complete pipeline.")
        return 0

    print_banner(vault_root)
    print(f"🎯 Selected pipeline actions: {', '.join(requested_steps)}")
    if args.dry_run:
        print("⚡ Global dry-run mode active")
    print()

    results: List[Tuple[str, str, str, float]] = []
    total_steps = len(requested_steps)
    step_index = 0

    for step_id, description, step_fn in PIPELINE_STEPS:
        if step_id not in requested_steps:
            continue

        step_index += 1
        print(f"{'─' * 72}")
        print(f"▶ [{step_index}/{total_steps}] Step: {description} (`--{step_id.replace('_', '-')}`)")
        print(f"{'─' * 72}")

        start_time = time.time()
        status = "SUCCESS"
        try:
            step_fn(args, vault_root)
        except Exception as e:
            status = "FAILED"
            print(f"\n❌ Error during '{step_id}': {e}", file=sys.stderr)
            if getattr(args, "fail_fast", False):
                elapsed = time.time() - start_time
                results.append((step_id, description, status, elapsed))
                print_summary(results)
                return 1
        finally:
            elapsed = time.time() - start_time
            if status == "SUCCESS":
                print(f"\n✔ [{step_index}/{total_steps}] {description} finished in {elapsed:.2f}s")

        results.append((step_id, description, status, elapsed))
        print()

    print_summary(results)

    # Return non-zero exit code if any step failed
    has_failure = any(s == "FAILED" for _, _, s, _ in results)
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
