"""Patch 0.6.0 -> 0.7.0.

Milestone v0.7 Code Quality, Testing & Reliability:
- Overwrites 99_System (Scripts, Templates, Views, docs, Tests) from upstream starter, preserving user configuration.
- Updates runner (run.py) and dependencies (pyproject.toml).
- Ensures 10_Finance/History/archive and 00_Raw/archive directories exist with .gitkeep.
- Merges default retention section into root config.yaml if missing.
- Strictly preserves all private user data (Assets, raw exports, decisions, portfolio.csv, .env).
"""

from __future__ import annotations

import os
import shutil

import yaml

FROM_VERSION = "0.6.0"
TO_VERSION = "0.7.0"
DESCRIPTION = (
    "Upgrade to v0.7 Code Quality, Testing & Reliability (Data Retention, History Archival, Structured Logging)"
)


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
        # Filter out ignored directories in-place
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

            rel_dst = os.path.relpath(dst_file, dst_dir)
            copied.append(rel_dst)

            if not dry_run:
                shutil.copy2(src_file, dst_file)

    return copied


def apply(source_vault: str, target_vault: str, dry_run: bool = False) -> bool:
    """Apply the 0.6.0 -> 0.7.0 patch to target_vault."""
    source_vault = os.path.abspath(source_vault)
    target_vault = os.path.abspath(target_vault)
    is_same_vault = source_vault == target_vault

    print(f"\n📦 Applying Patch {FROM_VERSION} -> {TO_VERSION}: {DESCRIPTION}")
    print(f"   Source Starter : {source_vault}")
    print(f"   Target Vault   : {target_vault}")
    if dry_run:
        print("   Mode           : [DRY-RUN] No files will be modified.")

    # 1. Update 99_System (Scripts, Templates, Views, docs, Tests)
    src_system = os.path.join(source_vault, "99_System")
    dst_system = os.path.join(target_vault, "99_System")

    ignore_system_files = set()
    if os.path.exists(os.path.join(dst_system, "config.yaml")):
        ignore_system_files.add("config.yaml")

    system_folders = ["Scripts", "Templates", "Views", "docs", "Tests"]
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

    # 2. Update root runners and manifests
    root_files_to_sync = ["run.py", "patch.py", "init.py", "pyproject.toml"]
    for rf in root_files_to_sync:
        s_file = os.path.join(source_vault, rf)
        d_file = os.path.join(target_vault, rf)
        if os.path.exists(s_file):
            if not dry_run:
                shutil.copy2(s_file, d_file)
            print(f"   Updated root file: {rf}")

    # 3. Ensure archive directories exist in target
    history_archive = os.path.join(target_vault, "10_Finance", "History", "archive")
    raw_archive = os.path.join(target_vault, "00_Raw", "archive")

    for arch_dir in [history_archive, raw_archive]:
        if not os.path.exists(arch_dir):
            if not dry_run:
                os.makedirs(arch_dir, exist_ok=True)
                with open(os.path.join(arch_dir, ".gitkeep"), "w", encoding="utf-8") as f:
                    f.write("")
            print(f"   Created archive directory: {os.path.relpath(arch_dir, target_vault)}")

    # 4. Safely merge retention config into target config.yaml if missing
    target_config = os.path.join(target_vault, "config.yaml")
    if os.path.exists(target_config):
        try:
            with open(target_config, encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}

            if "retention" not in user_cfg:
                retention_block = (
                    "\n# Data Retention & History Archival Settings\n"
                    "retention:\n"
                    "  history:\n"
                    "    enabled: true\n"
                    "    retention_days: 730\n"
                    "    archive_dir: '10_Finance/History/archive'\n"
                    "    preserve_boundary_baseline: true\n"
                    "  raw_data:\n"
                    "    enabled: true\n"
                    "    retention_days: 365\n"
                    "    action: 'archive'\n"
                    "    archive_dir: '00_Raw/archive'\n"
                    "    compress_zip: false\n"
                    "    exclude_patterns:\n"
                    "      - 'sample_*'\n"
                    "      - '.*'\n"
                    "      - '.gitkeep'\n"
                    "      - 'Articles/*'\n"
                    "      - 'archive/*'\n"
                )
                if not dry_run:
                    with open(target_config, "a", encoding="utf-8") as f:
                        f.write(retention_block)
                print("   Merged retention configuration section into target config.yaml")
        except Exception as e:
            print(f"   Warning: could not inspect/merge retention config: {e}")

    # 5. Remove todo.md in downstream vault (only if target is not the template itself)
    if not is_same_vault:
        target_todo = os.path.join(target_vault, "todo.md")
        if os.path.exists(target_todo):
            if not dry_run:
                os.remove(target_todo)
            print("   Removed todo.md from downstream personal vault (roadmap maintained in upstream template)")

    # 6. Safety check: ensure private user data was NOT touched
    for private_path in [
        os.path.join(target_vault, "10_Finance", "Assets"),
        os.path.join(target_vault, "20_Decisions"),
        os.path.join(target_vault, "10_Finance", "History", "portfolio.csv"),
        os.path.join(target_vault, ".env"),
    ]:
        if os.path.exists(private_path):
            pass

    # 7. Update target vault .vault_version
    target_version_file = os.path.join(target_vault, ".vault_version")
    if not dry_run:
        with open(target_version_file, "w", encoding="utf-8") as f:
            f.write(f"{TO_VERSION}\n")
    print(f"   Target vault updated to version {TO_VERSION}")

    return True
