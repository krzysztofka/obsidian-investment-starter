"""Patch 0.11.0 -> 0.12.0.

Milestone v0.12 Interactive Model Portfolio Configuration & Drift Checking:
- Synchronizes 99_System (Scripts including setup_model_portfolios.py and check_model_portfolios.py, Templates, Views, docs).
- Synchronizes .agents/ workspace skills and docs/adr/.
- Synchronizes root runners (init.py, run.py, patch.py), dashboards, and documentation.
- Normalizes any remaining min_trade_amount_pln keys in config.yaml to min_trade_amount while preserving all custom user settings.
"""

from __future__ import annotations

import os
import re
import shutil

FROM_VERSION = "0.11.0"
TO_VERSION = "0.12.0"
DESCRIPTION = "Upgrade to v0.12 Interactive Model Portfolio Configuration & Drift Checking"


def _copy_tree_preserving_config(
    src_dir: str,
    dst_dir: str,
    ignore_files: set[str],
    dry_run: bool = False,
) -> list[str]:
    """Recursively copy directory tree while ignoring specified files and patterns."""
    copied: list[str] = []
    if not os.path.exists(src_dir):
        return copied

    if not dry_run:
        os.makedirs(dst_dir, exist_ok=True)

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".pytest_cache", ".cache", ".git"}]

        rel_path = os.path.relpath(root, src_dir)
        target_root = os.path.join(dst_dir, rel_path) if rel_path != "." else dst_dir

        if not dry_run:
            os.makedirs(target_root, exist_ok=True)

        for f in files:
            if f in ignore_files or f.endswith(".pyc") or f.endswith(".log"):
                continue

            src_file = os.path.join(root, f)
            dst_file = os.path.join(target_root, f)

            if os.path.abspath(src_file) == os.path.abspath(dst_file):
                continue

            rel_dst = os.path.relpath(dst_file, dst_dir)
            copied.append(rel_dst)

            if not dry_run:
                shutil.copy2(src_file, dst_file)

    return copied


def apply(source_vault: str, target_vault: str, dry_run: bool = False) -> bool:
    """Apply the 0.11.0 -> 0.12.0 patch to target_vault."""
    source_vault = os.path.abspath(source_vault)
    target_vault = os.path.abspath(target_vault)
    is_same_vault = source_vault == target_vault

    print(f"\n📦 Applying Patch {FROM_VERSION} -> {TO_VERSION}: {DESCRIPTION}")
    print(f"   Source Starter : {source_vault}")
    print(f"   Target Vault   : {target_vault}")
    if dry_run:
        print("   Mode           : [DRY-RUN] No files will be modified.")

    # 1. Update 99_System core folders (Scripts, Templates, Views, docs)
    src_system = os.path.join(source_vault, "99_System")
    dst_system = os.path.join(target_vault, "99_System")

    ignore_system_files = set()
    if os.path.exists(os.path.join(dst_system, "config.yaml")):
        ignore_system_files.add("config.yaml")

    system_folders = ["Scripts", "Templates", "Views", "docs"]
    for folder in system_folders:
        src_f = os.path.join(src_system, folder)
        dst_f = os.path.join(dst_system, folder)
        if os.path.exists(src_f):
            copied = _copy_tree_preserving_config(
                src_f,
                dst_f,
                ignore_files=ignore_system_files,
                dry_run=dry_run,
            )
            print(f"   Updated 99_System/{folder} ({len(copied)} files)")

    # 2. Update .agents/ workspace skills and docs/adr/
    for extra_folder in (".agents", "docs"):
        src_extra = os.path.join(source_vault, extra_folder)
        dst_extra = os.path.join(target_vault, extra_folder)
        if os.path.exists(src_extra):
            copied_extra = _copy_tree_preserving_config(
                src_extra,
                dst_extra,
                ignore_files=set(),
                dry_run=dry_run,
            )
            print(f"   Updated {extra_folder}/ ({len(copied_extra)} files)")

    # 3. Normalize min_trade_amount_pln -> min_trade_amount in target config.yaml
    target_cfg_path = os.path.join(target_vault, "config.yaml")
    if os.path.exists(target_cfg_path):
        with open(target_cfg_path, encoding="utf-8") as f:
            cfg_content = f.read()
        if "min_trade_amount_pln:" in cfg_content:
            updated_cfg = re.sub(r"\bmin_trade_amount_pln:", "min_trade_amount:", cfg_content)
            if not dry_run:
                with open(target_cfg_path, "w", encoding="utf-8") as f:
                    f.write(updated_cfg)
            print("   Normalized min_trade_amount_pln -> min_trade_amount in config.yaml")

    # 4. Update root runners, manifests and documentation
    root_files_to_sync = [
        "run.py",
        "patch.py",
        "init.py",
        "pyproject.toml",
        "GEMINI.md",
        "Welcome.md",
        "Health.md",
        "GLOSSARY.md",
        "Overview.md",
        "Portfolio_performance.md",
        "Aggressive_portfolio.md",
        "Long_term_portfolio.md",
        "Safety_portfolio.md",
        "Alerts.md",
    ]
    for rf in root_files_to_sync:
        s_file = os.path.join(source_vault, rf)
        d_file = os.path.join(target_vault, rf)
        if os.path.exists(s_file):
            if os.path.abspath(s_file) != os.path.abspath(d_file):
                if not dry_run:
                    shutil.copy2(s_file, d_file)
                print(f"   Updated root file: {rf}")

    # 5. Clean downstream vault of tests and caches
    if not is_same_vault:
        downstream_tests = os.path.join(target_vault, "99_System", "Tests")
        if os.path.exists(downstream_tests):
            if not dry_run:
                shutil.rmtree(downstream_tests, ignore_errors=True)
            print("   Pruned development tests (99_System/Tests/)")

        target_todo = os.path.join(target_vault, "todo.md")
        if os.path.exists(target_todo):
            if not dry_run:
                try:
                    os.remove(target_todo)
                except OSError:
                    pass
            print("   Removed todo.md (backlog maintained upstream)")

    # Prune legacy 99_System/config.yaml if root config.yaml exists
    legacy_sys_cfg = os.path.join(target_vault, "99_System", "config.yaml")
    if os.path.exists(target_cfg_path) and os.path.exists(legacy_sys_cfg):
        if not dry_run:
            try:
                os.remove(legacy_sys_cfg)
            except OSError:
                pass
        print("   Removed obsolete legacy 99_System/config.yaml (canonical config is root config.yaml)")

    # 6. Update target vault .vault_version
    target_version_file = os.path.join(target_vault, ".vault_version")
    if not dry_run:
        with open(target_version_file, "w", encoding="utf-8") as f:
            f.write(f"{TO_VERSION}\n")
    print(f"   Target vault updated to version {TO_VERSION}")

    return True
