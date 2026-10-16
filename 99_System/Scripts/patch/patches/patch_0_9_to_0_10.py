"""Patch 0.9.0 -> 0.10.0.

Milestone v0.10 Configurable Base Portfolio Currency & Multi-Currency FX Engine:
- Synchronizes 99_System (Scripts, Templates, Views, docs) including localized DataviewJS views.
- Synchronizes .agents/ workspace skills.
- Non-destructively merges localization: section into config.yaml if missing (default PLN, zł, suffix).
- Migrates config.yaml model portfolio keys: renames min_trade_amount_pln to min_trade_amount.
- Non-destructively migrates 10_Finance/Assets/*.md notes: ensures value_base is populated from value_pln.
- Updates 10_Finance/History/portfolio.csv header from value_pln to value_base if needed.
- Synchronizes root runners, dashboards (Overview.md, Safety_portfolio.md, Long_term_portfolio.md, Aggressive_portfolio.md, Alerts.md), GLOSSARY.md, and documentation.
- Strictly preserves all private user data (asset notes content, decisions, history records, raw exports, .env).
"""

from __future__ import annotations

import os
import re
import shutil

FROM_VERSION = "0.9.0"
TO_VERSION = "0.10.0"
DESCRIPTION = "Upgrade to v0.10 Configurable Base Portfolio Currency & Multi-Currency FX Engine"


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


def _merge_localization_config(target_vault: str, dry_run: bool = False) -> bool:
    """Non-destructively append default localization section to target config.yaml if missing."""
    config_path = os.path.join(target_vault, "config.yaml")
    if not os.path.exists(config_path):
        return False

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    if "localization:" in content:
        return False

    default_block = (
        "\n# Regional & Currency Localization\n"
        "localization:\n"
        '  base_currency: "PLN"\n'
        '  currency_symbol: "zł"\n'
        '  symbol_position: "suffix"\n'
    )

    if not dry_run:
        with open(config_path, "a", encoding="utf-8") as f:
            f.write(default_block)
    print("   Merged default localization section into config.yaml")
    return True


def _migrate_min_trade_amount(target_vault: str, dry_run: bool = False) -> bool:
    """Rename min_trade_amount_pln to min_trade_amount in target config.yaml."""
    config_path = os.path.join(target_vault, "config.yaml")
    if not os.path.exists(config_path):
        return False

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    if "min_trade_amount_pln" not in content:
        return False

    new_content = content.replace("min_trade_amount_pln:", "min_trade_amount:")
    if new_content != content:
        if not dry_run:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        print("   Renamed min_trade_amount_pln to min_trade_amount in config.yaml")
        return True
    return False


def _migrate_asset_notes(target_vault: str, dry_run: bool = False) -> int:
    """Ensure value_base is populated from value_pln in 10_Finance/Assets/*.md notes."""
    assets_dir = os.path.join(target_vault, "10_Finance", "Assets")
    if not os.path.isdir(assets_dir):
        return 0

    migrated = 0
    for fname in os.listdir(assets_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(assets_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        if "value_base:" not in content and "value_pln:" in content:
            new_content = re.sub(
                r"(\n([ \t]*)value_pln:[ \t]*([^\n\r]+))",
                r"\n\2value_base: \3\1",
                content,
                count=1,
            )
            if new_content != content:
                migrated += 1
                if not dry_run:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)

    if migrated > 0:
        print(f"   Migrated {migrated} asset notes (added value_base)")
    return migrated


def _migrate_portfolio_history_csv(target_vault: str, dry_run: bool = False) -> bool:
    """Replace value_pln with value_base in 10_Finance/History/portfolio.csv header."""
    csv_path = os.path.join(target_vault, "10_Finance", "History", "portfolio.csv")
    if not os.path.exists(csv_path):
        return False

    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return False

    header = lines[0]
    if "value_pln" in header:
        new_header = header.replace("value_pln", "value_base")
        lines[0] = new_header
        if not dry_run:
            with open(csv_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        print("   Updated portfolio.csv header from value_pln to value_base")
        return True
    return False


def apply(source_vault: str, target_vault: str, dry_run: bool = False) -> bool:
    """Apply the 0.9.0 -> 0.10.0 patch to target_vault."""
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

    # 2. Update .agents/ workspace skills
    src_agents = os.path.join(source_vault, ".agents")
    dst_agents = os.path.join(target_vault, ".agents")
    if os.path.exists(src_agents):
        copied_agents = _copy_tree_preserving_config(
            src_agents,
            dst_agents,
            ignore_files=set(),
            dry_run=dry_run,
        )
        print(f"   Updated .agents/ workspace customizations ({len(copied_agents)} files)")

    # 3. Update root runners, manifests and documentation
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

    # 4. Non-destructively merge localization into config.yaml if needed
    _merge_localization_config(target_vault, dry_run=dry_run)

    # 5. Rename min_trade_amount_pln to min_trade_amount in config.yaml
    _migrate_min_trade_amount(target_vault, dry_run=dry_run)

    # 6. Migrate asset notes: add value_base if missing
    _migrate_asset_notes(target_vault, dry_run=dry_run)

    # 7. Migrate history portfolio.csv header
    _migrate_portfolio_history_csv(target_vault, dry_run=dry_run)

    # 8. Clean downstream vault of tests and caches
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

    # 9. Update target vault .vault_version
    target_version_file = os.path.join(target_vault, ".vault_version")
    if not dry_run:
        with open(target_version_file, "w", encoding="utf-8") as f:
            f.write(f"{TO_VERSION}\n")
    print(f"   Target vault updated to version {TO_VERSION}")

    return True
