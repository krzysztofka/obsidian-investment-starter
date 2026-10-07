#!/usr/bin/env python3
"""Vault Patch & Starter Updater CLI.

Entry point for applying sequential version patches from upstream starter
to downstream user vaults.

Usage:
  python patch.py --list
  python patch.py --version
  python patch.py --target ../trader --dry-run
  python patch.py --target ../trader
"""

import os
import sys

# Add scripts directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "99_System", "Scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from patch.patch_engine import PatchEngine, get_vault_version


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Upgrade and patch vault from upstream starter repository.",
        epilog="""\
examples:
  python patch.py --list                      List available patches
  python patch.py --version                   Show current vault version
  python patch.py --target ../trader --dry-run Preview patch updates for target vault
  python patch.py --target ../trader          Apply patch updates to target vault
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        type=str,
        default=None,
        help="Target vault directory to upgrade. Defaults to current vault.",
    )
    parser.add_argument(
        "-s",
        "--source",
        dest="source",
        type=str,
        default=SCRIPT_DIR,
        help="Upstream starter vault directory. Defaults to this repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate patch without writing any files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-applying patch even if version is up-to-date.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all registered patches.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print vault version and exit.",
    )

    args = parser.parse_args()

    engine = PatchEngine(source_vault=args.source)

    if args.version:
        tgt = args.target or engine.source_vault
        print(f"v{get_vault_version(tgt)}")
        return 0

    if args.list:
        engine.list_patches()
        return 0

    target_path = args.target or engine.source_vault
    success = engine.run_patch(target_vault=target_path, dry_run=args.dry_run, force=args.force)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
