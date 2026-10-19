"""Interactive Vault Scaffolding & Modular Initial Setup Engine.

Guides the user step-by-step through configuring a new personal investment vault
bootstrapped from the starter repository, or reconfiguring individual steps.
"""

import os
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = SCRIPT_DIR
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, SCRIPTS_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import platforms  # noqa: F401
from init_steps import (
    BaseInitStep,
    InitContext,
    InitStepRegistry,
    update_env_variable,
)
from init_steps.step_01_vault_mode import (
    _copy_tree_filtered,
    ensure_core_vault_files,
    prompt_clean_mode,
    purge_sample_data,
    scaffold_target_vault,
)
from init_steps.step_02_brokers import (
    prompt_degiro_portfolio,
    prompt_exante_api_credentials,
    prompt_exante_mode,
    prompt_platform_selection,
)
from init_steps.step_03_localization import (
    _update_localization_in_config,
    configure_localization,
    prompt_base_currency_selection,
)
from init_steps.step_04_model_portfolios import (
    MODEL_PORTFOLIO_PRESETS,
    _update_model_portfolios_in_config,
    _update_single_stock_cap_in_config,
    configure_model_portfolios,
    prompt_max_single_stock_pct,
    prompt_model_portfolio_preset,
)
from init_steps.step_05_agent_profile import (
    _update_user_profile_in_config,
    configure_user_profile,
    prompt_finnhub_api_key,
)
from init_steps.step_06_diagnostics import verify_python_dependencies
from platforms.base import PlatformRegistry

_update_env_variable = update_env_variable

__all__ = [
    "VAULT_ROOT",
    "BaseInitStep",
    "InitContext",
    "InitStepRegistry",
    "MODEL_PORTFOLIO_PRESETS",
    "_copy_tree_filtered",
    "_update_env_variable",
    "_update_localization_in_config",
    "_update_model_portfolios_in_config",
    "_update_single_stock_cap_in_config",
    "_update_user_profile_in_config",
    "configure_localization",
    "configure_model_portfolios",
    "configure_user_profile",
    "ensure_core_vault_files",
    "init_vault",
    "list_init_steps",
    "prompt_base_currency_selection",
    "prompt_clean_mode",
    "prompt_degiro_portfolio",
    "prompt_exante_api_credentials",
    "prompt_exante_mode",
    "prompt_finnhub_api_key",
    "prompt_max_single_stock_pct",
    "prompt_model_portfolio_preset",
    "prompt_platform_selection",
    "prompt_step_selection_menu",
    "purge_sample_data",
    "scaffold_target_vault",
    "verify_python_dependencies",
]


def list_init_steps() -> list[dict[str, Any]]:
    """Return metadata for all registered initialization steps in execution order."""
    steps = InitStepRegistry.get_ordered_steps()
    return [
        {
            "step_number": s.step_number,
            "step_id": s.step_id,
            "title": s.title,
            "description": s.description,
            "aliases": s.aliases,
        }
        for s in steps
    ]


def prompt_step_selection_menu() -> str | None:
    """Interactive menu when running init.py on an already-initialized vault.

    Returns None for full wizard, or the selected step_id for single-step reconfiguration.
    """
    steps = InitStepRegistry.get_ordered_steps()
    print("Detected existing vault configuration. Select setup mode:")
    print("  [A] Run Full Initialization Wizard (All steps 1–6) [Default]")
    for s in steps:
        print(f"  [{s.step_number}] Reconfigure Step {s.step_number} ({s.step_id}): {s.description}")

    try:
        choice = input(f"\nEnter choice [A, 1-{len(steps)}, step name, or Enter for All]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice or choice.lower() in ("a", "all", "full"):
        return None

    resolved = InitStepRegistry.get(choice)
    if resolved:
        return resolved.step_id

    print(f"   ⚠️ Unrecognized step '{choice}'. Running full wizard.")
    return None


def init_vault(
    target_vault: str | None = None,
    interactive: bool = True,
    clean: bool | None = None,
    force: bool = False,
    exante_mode: str | None = None,
    step: str | None = None,
    preset_id: str | None = None,
) -> bool:
    """Initialize a new vault or reconfigure a specific initialization step."""
    target_dir = os.path.abspath(target_vault or VAULT_ROOT)

    print("=" * 72)
    print("🚀  INVESTMENT SECOND BRAIN — VAULT INITIALIZER")
    print("=" * 72)
    print(f"📁 Target Vault Directory: {target_dir}")
    print("=" * 72)
    print()

    # If --step menu or --step ask is passed, show interactive step selection menu
    effective_step = step
    if effective_step and effective_step.lower().strip() in ("menu", "select", "ask"):
        effective_step = prompt_step_selection_menu()

    ctx = InitContext(
        source_vault=VAULT_ROOT,
        target_dir=target_dir,
        interactive=interactive,
        clean=clean,
        force=force,
        exante_mode=exante_mode,
        preset_id=preset_id,
        single_step_mode=bool(effective_step),
    )

    if effective_step:
        step_obj = InitStepRegistry.get(effective_step)
        if not step_obj:
            valid_ids = ", ".join(f"{s.step_number}:{s.step_id}" for s in InitStepRegistry.get_ordered_steps())
            print(f"❌ Unknown initialization step: '{effective_step}'. Valid steps: {valid_ids}", file=sys.stderr)
            return False

        # Ensure core files (.env, config.yaml) exist before running any standalone step
        if step_obj.step_id != "vault_mode":
            ensure_core_vault_files(VAULT_ROOT, target_dir)

        ok = step_obj.run(ctx)
        if ok:
            print("\n" + "=" * 72)
            print(f"✨ Step '{step_obj.step_id}' completed successfully!")
            print("=" * 72)
        return ok

    # Run all steps in sequence
    ordered_steps = InitStepRegistry.get_ordered_steps()
    for step_obj in ordered_steps:
        ok = step_obj.run(ctx)
        if not ok:
            return False

    all_platforms = PlatformRegistry.get_all(base_dir=target_dir)
    selected_platform_ids = ctx.selected_platform_ids or list(all_platforms.keys())
    effective_exante_mode = ctx.exante_mode or "csv"

    print("\n" + "=" * 72)
    print("✨ Vault initialization completed successfully!")
    print("=" * 72)
    print("Next steps:")
    active_folders = [
        all_platforms[pid].raw_folder
        for pid in selected_platform_ids
        if pid in all_platforms and not (pid == "exante" and effective_exante_mode == "api")
    ]
    api_providers = "Finnhub, Exante" if effective_exante_mode == "api" else "Finnhub"
    if ctx.clean:
        if active_folders:
            print(f"  1. Add your real broker exports to 00_Raw/ ({', '.join(active_folders)}).")
        print(f"  2. Configure your API keys in .env ({api_providers}).")
        print("  3. Open this directory as a Vault in Obsidian (Dataview & Charts plugins pre-configured).")
        print("  4. Run 'python run.py --health' to inspect your integration diagnostics (Health.md).")
        print("  5. Run 'python run.py --all' to execute your first import & analytics.")
    else:
        print("  1. Open this directory as a Vault in Obsidian to explore the sample dashboards and assets.")
        if active_folders:
            print(f"  2. To import real data later, place statements in 00_Raw/ ({', '.join(active_folders)}).")
        print("  3. To reset and purge demo assets when ready, run 'python init.py --clean'.")
        print("  4. To reconfigure any single step later, run 'python init.py --step <step_name>'.")
        print("  5. Run 'python run.py --all' to execute your portfolio intelligence pipeline.")
    print("=" * 72)
    return True


if __name__ == "__main__":
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
        help="Run without prompting.",
    )
    args = parser.parse_args()

    if args.list_steps:
        print("\nAvailable Vault Initialization Steps:")
        for s_info in list_init_steps():
            aliases_str = ", ".join(s_info["aliases"])
            print(
                f"  [{s_info['step_number']}] {s_info['step_id']:<18} — {s_info['description']} (aliases: {aliases_str})"
            )
        sys.exit(0)

    clean_mode = None
    if args.clean:
        clean_mode = True
    elif args.demo:
        clean_mode = False

    init_kwargs: dict[str, Any] = {
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

    success = init_vault(**init_kwargs)
    sys.exit(0 if success else 1)
