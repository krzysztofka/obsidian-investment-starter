#!/usr/bin/env python3
"""Vault Initializer CLI.

Quickstart setup script to initialize and configure a new vault from this starter,
or reconfigure individual setup steps.

Usage:
  python init.py
  python init.py --target ../my-vault
  python init.py --step brokers
  python init.py --step model_portfolios
  python init.py --list-steps
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "99_System", "Scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from init_vault import MODEL_PORTFOLIO_PRESETS, init_vault, list_init_steps


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
        "-s",
        "--step",
        dest="step",
        nargs="?",
        const="menu",
        type=str,
        default=None,
        help="Run a single initialization step (e.g. 'vault_mode', 'brokers', 'localization', 'model_portfolios', 'agent_profile', 'diagnostics', or omit value for interactive menu).",
    )
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="List all available initialization steps and exit.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=None,
        help="Initialize as a Clean Vault (wipe sample assets, raw demo exports & reset history).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=None,
        help="Initialize as a Demo Vault (preserve sample assets and demonstration history).",
    )
    parser.add_argument(
        "--exante-mode",
        dest="exante_mode",
        choices=["csv", "api"],
        default=None,
        help="Configure Exante default import mode ('csv' or 'api').",
    )
    parser.add_argument(
        "--preset",
        dest="preset",
        choices=list(MODEL_PORTFOLIO_PRESETS.keys()),
        default=None,
        help="Model portfolio preset ('balanced', 'conservative', 'aggressive_growth', 'classic').",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force initialization even if target directory is not empty.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run non-interactively.",
    )

    args = parser.parse_args()

    if args.list_steps:
        print("\nAvailable Vault Initialization Steps:")
        for s_info in list_init_steps():
            aliases_str = ", ".join(s_info["aliases"])
            print(
                f"  [{s_info['step_number']}] {s_info['step_id']:<18} — {s_info['description']} (aliases: {aliases_str})"
            )
        return 0

    clean_mode = None
    if args.clean:
        clean_mode = True
    elif args.demo:
        clean_mode = False

    init_kwargs = {
        "target_vault": args.target,
        "interactive": not args.non_interactive,
        "clean": clean_mode,
        "force": args.force,
    }
    if args.exante_mode is not None:
        init_kwargs["exante_mode"] = args.exante_mode
    if args.step is not None:
        init_kwargs["step"] = args.step
    if args.preset is not None:
        init_kwargs["preset_id"] = args.preset

    ok = init_vault(**init_kwargs)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
