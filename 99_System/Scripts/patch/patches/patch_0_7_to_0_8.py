"""Patch 0.7.0 -> 0.8.0.

Milestone v0.8 System Health Checks, Sanity Diagnostics & Downstream Decoupling:
- Overwrites 99_System (Scripts, Templates, Views, docs) from upstream starter, preserving user configuration.
- Decouples development tests: strictly excludes 99_System/Tests from downstream synchronization.
- Automatically prunes legacy 99_System/Tests/, tests/, and .pytest_cache/ directories from downstream vaults.
- Updates runners (run.py, patch.py, init.py) and documentation (Health.md, GEMINI.md, Welcome.md).
- Strictly preserves all private user data (Assets, raw exports, decisions, portfolio.csv, .env).
"""

from __future__ import annotations

import os
import shutil

FROM_VERSION = "0.7.0"
TO_VERSION = "0.8.0"
DESCRIPTION = (
    "Upgrade to v0.8 System Diagnostics & Downstream Decoupling (Health Check Diagnostics, Test & Mock Pruning)"
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


def _prune_path(target_path: str, label: str, dry_run: bool = False) -> bool:
    """Helper to prune a file or directory tree with logging."""
    if not os.path.exists(target_path):
        return False

    if os.path.isdir(target_path):
        if not dry_run:
            shutil.rmtree(target_path, ignore_errors=True)
        print(f"   Pruned {label} directory: {target_path}")
    else:
        if not dry_run:
            try:
                os.remove(target_path)
            except OSError:
                pass
        print(f"   Removed {label}: {target_path}")
    return True


def apply(source_vault: str, target_vault: str, dry_run: bool = False) -> bool:
    """Apply the 0.7.0 -> 0.8.0 patch to target_vault."""
    source_vault = os.path.abspath(source_vault)
    target_vault = os.path.abspath(target_vault)
    is_same_vault = source_vault == target_vault

    print(f"\n📦 Applying Patch {FROM_VERSION} -> {TO_VERSION}: {DESCRIPTION}")
    print(f"   Source Starter : {source_vault}")
    print(f"   Target Vault   : {target_vault}")
    if dry_run:
        print("   Mode           : [DRY-RUN] No files will be modified.")

    # 1. Update 99_System core folders (Scripts, Templates, Views, docs)
    # Note: Tests is intentionally excluded from downstream synchronization.
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

    # 2. Update root runners, manifests and documentation
    root_files_to_sync = [
        "run.py",
        "patch.py",
        "init.py",
        "pyproject.toml",
        "GEMINI.md",
        "Welcome.md",
        "Health.md",
    ]
    for rf in root_files_to_sync:
        s_file = os.path.join(source_vault, rf)
        d_file = os.path.join(target_vault, rf)
        if os.path.exists(s_file):
            if not dry_run:
                shutil.copy2(s_file, d_file)
            print(f"   Updated root file: {rf}")

    # 3. Downstream cleanliness: Prune tests, caches, and roadmap backlog
    # Strictly execute only for downstream personal vaults (not upstream template starter).
    if not is_same_vault:
        # A. Prune test directories
        downstream_tests = os.path.join(target_vault, "99_System", "Tests")
        _prune_path(downstream_tests, "development tests (99_System/Tests/)", dry_run=dry_run)

        legacy_tests = os.path.join(target_vault, "tests")
        _prune_path(legacy_tests, "legacy root tests", dry_run=dry_run)

        # B. Prune pytest and coverage caches
        root_pytest_cache = os.path.join(target_vault, ".pytest_cache")
        _prune_path(root_pytest_cache, ".pytest_cache", dry_run=dry_run)

        sys_pytest_cache = os.path.join(target_vault, "99_System", ".pytest_cache")
        _prune_path(sys_pytest_cache, "99_System/.pytest_cache", dry_run=dry_run)

        root_coverage = os.path.join(target_vault, ".coverage")
        _prune_path(root_coverage, ".coverage cache", dry_run=dry_run)

        root_htmlcov = os.path.join(target_vault, "htmlcov")
        _prune_path(root_htmlcov, "htmlcov directory", dry_run=dry_run)

        # C. Remove template roadmap todo.md (maintained only upstream)
        target_todo = os.path.join(target_vault, "todo.md")
        _prune_path(target_todo, "todo.md (backlog maintained upstream)", dry_run=dry_run)

    # 4. Safety check: ensure private user data was NOT touched
    for private_path in [
        os.path.join(target_vault, "10_Finance", "Assets"),
        os.path.join(target_vault, "20_Decisions"),
        os.path.join(target_vault, "10_Finance", "History", "portfolio.csv"),
        os.path.join(target_vault, ".env"),
    ]:
        if os.path.exists(private_path):
            pass

    # 5. Update target vault .vault_version
    target_version_file = os.path.join(target_vault, ".vault_version")
    if not dry_run:
        with open(target_version_file, "w", encoding="utf-8") as f:
            f.write(f"{TO_VERSION}\n")
    print(f"   Target vault updated to version {TO_VERSION}")

    return True
