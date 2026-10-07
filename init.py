#!/usr/bin/env python3
"""Vault Initializer CLI.

Quickstart setup script to initialize and configure a new vault from this starter.

Usage:
  python init.py
  python init.py --target ../my-vault
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "99_System", "Scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from init_vault import init_vault


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Initialize new investment vault from starter.")
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        type=str,
        default=None,
        help="Target directory to initialize. Defaults to current directory.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run non-interactively.",
    )

    args = parser.parse_args()
    ok = init_vault(target_vault=args.target, interactive=not args.non_interactive)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
