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

import argparse
import os
import re
import sys
import time
from typing import Any

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

    ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def __init__(self, stream, log_path: str):
        self.stream = stream
        self.log_path = log_path
        self._file = None
        self._line_buffer = ""
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
                # Strip ANSI sequences to keep log file clean plaintext
                clean_chunk = self.ANSI_ESCAPE_RE.sub("", data)
                self._line_buffer += clean_chunk
                if "\n" in self._line_buffer:
                    lines = self._line_buffer.replace("\r\n", "\n").split("\n")
                    for line in lines[:-1]:
                        final_line = line.split("\r")[-1]
                        self._file.write(final_line + "\n")
                    self._line_buffer = lines[-1]
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
                if self._line_buffer:
                    final_line = self._line_buffer.split("\r")[-1]
                    if final_line:
                        self._file.write(final_line + "\n")
                    self._line_buffer = ""
                self._file.flush()
            except Exception:
                pass

    def close(self):
        try:
            self.flush()
        except Exception:
            pass
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def isatty(self):
        return getattr(self.stream, "isatty", lambda: False)()


# Enable output teeing to 99_System/runner.log
sys.stdout = TeeLogger(sys.stdout, LOG_FILE_PATH)
sys.stderr = TeeLogger(sys.stderr, LOG_FILE_PATH)


# ==============================================================================
# Pipeline Step Implementations
# ==============================================================================


def run_import_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute broker asset import."""
    from import_assets import import_assets
    from platforms.common import load_import_config

    platform = getattr(args, "platform", None)
    file_path = getattr(args, "file", None)
    use_api = getattr(args, "use_api", None)
    use_csv = getattr(args, "use_csv", False)
    account_id = getattr(args, "account_id", None)
    max_workers = getattr(args, "max_workers", None)

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
    else:
        from platforms.base import PlatformRegistry

        enabled_platforms = PlatformRegistry.get_enabled(base_dir=vault_root)
        enabled_names = ", ".join(p.display_name for p in enabled_platforms.values()) if enabled_platforms else "None"
        print(f"   Target: Enabled platforms ({enabled_names})")

    show_progress = not getattr(args, "no_progress", False)
    results = import_assets(
        platform=platform,
        file=file_path,
        base_dir=vault_root,
        use_api=effective_use_api,
        account_id=account_id,
        max_workers=max_workers,
        show_progress=show_progress,
    )
    total_imported = sum(results.values()) if isinstance(results, dict) else 0
    print(f"   Import completed. Total positions processed: {total_imported}")
    return {"status": "ok", "details": results, "count": total_imported}


def run_update_rates_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute currency FX rates update and PLN valuation calculation."""
    from update_currencies import update_currencies

    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    max_workers = getattr(args, "max_workers", None)
    show_progress = not getattr(args, "no_progress", False)
    print(f"💱 Updating live FX rates and PLN values in: {assets_dir}...")
    update_currencies(assets_dir, max_workers=max_workers, base_dir=vault_root, show_progress=show_progress)
    return {"status": "ok"}


def run_macro_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute macroeconomic dashboard synchronization."""
    from sync_macro import sync_macro

    macro_path = os.path.join(vault_root, "10_Finance", "Macro.md")
    dry_run = getattr(args, "dry_run", False)

    print("🌐 Synchronizing macroeconomic indicators, yields & rates...")
    if dry_run:
        print("   Mode: DRY-RUN (no files will be saved)")

    result = sync_macro(macro_path=macro_path, dry_run=dry_run)
    return {"status": "ok", "details": result}


def run_sync_etfs_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute ETF top holdings and cross-exposure synchronization."""
    from sync_etf_holdings import sync_all_etfs

    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    holdings_dir = os.path.join(vault_root, "10_Finance", "ETF_Holdings")
    target_etf = getattr(args, "etf", None)
    limit = getattr(args, "limit", None)
    dry_run = getattr(args, "dry_run", False)
    max_workers = getattr(args, "max_workers", None)
    show_progress = not getattr(args, "no_progress", False)

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
        max_workers=max_workers,
        show_progress=show_progress,
    )
    return {"status": "ok"}


def run_alerts_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
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


def run_history_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute portfolio historical snapshot synchronization."""
    from history.update_portfolio import update_portfolio_history

    print("📜 Synchronizing portfolio history timeline into portfolio.csv...")
    csv_file = update_portfolio_history(base_dir=vault_root)
    print(f"   History synchronized at: {csv_file}")
    return {"status": "ok", "file": csv_file}


def run_export_template_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute clean template repository export."""
    from export_template import export_template

    target_dir = getattr(args, "target_dir", None)
    exported_path = export_template(target_dir=target_dir)
    return {"status": "ok", "target_dir": exported_path}


def run_patch_step(args: argparse.Namespace, vault_root: str) -> dict[str, Any]:
    """Execute vault version patching and synchronization."""
    from patch.patch_engine import PatchEngine

    target_vault = getattr(args, "sync_vault_path", None) or getattr(args, "target", None)
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)

    engine = PatchEngine(source_vault=vault_root)
    target = target_vault or vault_root
    ok = engine.run_patch(target_vault=target, dry_run=dry_run, force=force)
    return {"status": "ok" if ok else "failed", "target": target}


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
    ("patch", "Patch and synchronize vault version", run_patch_step),
]


def print_banner(vault_root: str, max_workers: int | None = None):
    from platforms.common import get_max_workers

    workers = get_max_workers(max_workers, base_dir=vault_root)
    cpu_count = os.cpu_count() or "N/A"
    print("=" * 72)
    print("🚀  INVESTMENT SECOND BRAIN — UNIFIED RUNNER")
    print("=" * 72)
    print(f"📁 Vault Root : {vault_root}")
    print(f"⚡ CPU Threads: {cpu_count} detected | Concurrency: {workers} workers")
    print(f"🕒 Timestamp  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)
    print()


def print_summary(results: list[tuple[str, str, str, float]], use_rich: bool = True):
    try:
        from rich.table import Table
        from ui_progress import get_console

        console = get_console() if use_rich else None
    except ImportError:
        console = None

    if console and console.is_terminal:
        print()
        table = Table(
            title="📋  EXECUTION SUMMARY REPORT", show_header=True, header_style="bold cyan", border_style="dim"
        )
        table.add_column("Step", style="bold", width=16)
        table.add_column("Description", width=42)
        table.add_column("Status", width=12)
        table.add_column("Duration", justify="right", width=10)

        total_duration = 0.0
        all_success = True

        for step_id, description, status, duration in results:
            total_duration += duration
            if status == "SUCCESS":
                status_str = "[bold green]✅ SUCCESS[/bold green]"
            elif status == "FAILED":
                status_str = "[bold red]❌ FAILED[/bold red]"
                all_success = False
            else:
                status_str = "[bold yellow]⏭️ SKIPPED[/bold yellow]"
            table.add_row(step_id, description, status_str, f"{duration:.2f}s")

        console.print(table)
        status_msg = (
            "[bold green]✨ All requested actions completed successfully![/bold green]"
            if all_success
            else "[bold red]⚠️  One or more actions failed. Check logs above.[/bold red]"
        )
        print(f"Total Duration : {total_duration:.2f}s")
        console.print(f"Status         : {status_msg}")
        print("=" * 72)
        return

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
  python run.py --import                   Import portfolio form all platforms
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
        "-i",
        "--import",
        dest="action_import",
        action="store_true",
        help="Import broker positions from Degiro / Exante / mBM CSV exports or REST API.",
    )
    actions_group.add_argument(
        "-r",
        "--update-rates",
        "--rates",
        dest="action_update_rates",
        action="store_true",
        help="Refresh currency FX rates to PLN and update asset valuations.",
    )
    actions_group.add_argument(
        "-m",
        "--macro",
        "--sync-macro",
        dest="action_macro",
        action="store_true",
        help="Synchronize macroeconomic indicators, Treasury yields, and rates to Macro.md.",
    )
    actions_group.add_argument(
        "-s",
        "--sync-etfs",
        dest="action_sync_etfs",
        action="store_true",
        help="Synchronize ETF top holdings, overlap & exposures.",
    )
    actions_group.add_argument(
        "-a",
        "--alerts",
        dest="action_alerts",
        action="store_true",
        help="Scan and evaluate portfolio alerts (Alert Rules Engine).",
    )
    actions_group.add_argument(
        "-H",
        "--history",
        dest="action_history",
        action="store_true",
        help="Synchronize portfolio historical timeline into portfolio.csv.",
    )
    actions_group.add_argument(
        "--export-template",
        dest="action_export_template",
        action="store_true",
        help="Export clean template repository to ../obsidian-investment-starter.",
    )
    actions_group.add_argument(
        "--patch",
        dest="action_patch",
        action="store_true",
        help="Upgrade/patch vault using sequential migration patches.",
    )
    actions_group.add_argument(
        "--sync-vault",
        dest="sync_vault_path",
        type=str,
        default=None,
        metavar="TARGET_PATH",
        help="Synchronize and patch updates into target downstream vault (e.g., ../trader).",
    )

    # Platform extensions management
    platform_opts = parser.add_argument_group("platform extensions")
    platform_opts.add_argument(
        "--list-platforms",
        action="store_true",
        help="List available platform extensions and their enabled status.",
    )
    platform_opts.add_argument(
        "--enable-platform",
        dest="enable_platform",
        type=str,
        default=None,
        metavar="PLATFORM_ID",
        help="Enable a platform extension in config.yaml.",
    )
    platform_opts.add_argument(
        "--disable-platform",
        dest="disable_platform",
        type=str,
        default=None,
        metavar="PLATFORM_ID",
        help="Disable a platform extension in config.yaml.",
    )

    # Step-specific fine-tuning options
    step_opts = parser.add_argument_group("action options")
    step_opts.add_argument(
        "-p",
        "--platform",
        type=str,
        default=None,
        help="[--import] Broker platform (e.g., 'pko_bp_bonds', 'mbank_ike', 'mbank_ikze', 'degiro', 'exante'). Default: enabled platforms.",
    )

    step_opts.add_argument(
        "-f",
        "--file",
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
        "-w",
        "--workers",
        dest="max_workers",
        type=int,
        default=None,
        help="Number of concurrent worker threads (defaults to CPU hardware threads count).",
    )
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
        "--force",
        action="store_true",
        help="Force re-applying patch or action even if already up-to-date.",
    )
    global_opts.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        default=False,
        help="Disable interactive rich progress bars (useful for headless CI or simple log outputs).",
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

    # Platform management actions
    if args.list_platforms:
        from platforms.base import PlatformRegistry

        print("\nRegistered Platform Extensions:")
        print(f"{'ID':<16} {'Display Name':<20} {'Raw Folder':<16} {'Enabled':<10}")
        print("-" * 65)
        for item in PlatformRegistry.list_platforms(base_dir=vault_root):
            status = "✓ Yes" if item["enabled"] else "✗ No"
            print(f"{item['id']:<16} {item['display_name']:<20} {item['raw_folder']:<16} {status:<10}")
        print()
        return 0

    if args.enable_platform:
        from platforms.base import PlatformRegistry

        PlatformRegistry.set_platform_enabled(args.enable_platform, True, base_dir=vault_root)
        print(f"✓ Platform '{args.enable_platform}' enabled in config.yaml.")
        return 0

    if args.disable_platform:
        from platforms.base import PlatformRegistry

        PlatformRegistry.set_platform_enabled(args.disable_platform, False, base_dir=vault_root)
        print(f"✓ Platform '{args.disable_platform}' disabled in config.yaml.")
        return 0

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
    if args.action_patch or args.sync_vault_path:
        requested_steps.append("patch")

    # If no action is specified, print help and exit cleanly
    if not requested_steps:
        print_banner(vault_root, max_workers=args.max_workers)
        parser.print_help()
        print("\n💡 Tip: Run 'python run.py --all' to execute the complete pipeline.")
        return 0

    print_banner(vault_root, max_workers=args.max_workers)
    print(f"🎯 Selected pipeline actions: {', '.join(requested_steps)}")
    if args.dry_run:
        print("⚡ Global dry-run mode active")
    print()

    results: list[tuple[str, str, str, float]] = []
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
                print_summary(results, use_rich=not getattr(args, "no_progress", False))
                return 1
        finally:
            elapsed = time.time() - start_time
            if status == "SUCCESS":
                print(f"\n✔ [{step_index}/{total_steps}] {description} finished in {elapsed:.2f}s")

        results.append((step_id, description, status, elapsed))
        print()

    print_summary(results, use_rich=not getattr(args, "no_progress", False))

    # Return non-zero exit code if any step failed
    has_failure = any(s == "FAILED" for _, _, s, _ in results)
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
