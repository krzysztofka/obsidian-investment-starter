"""Step 2: Broker Platform Selection and Per-Broker Configuration Sub-steps."""

import os
from collections.abc import Callable
from typing import Any

import platforms  # noqa: F401
from platforms.base import PlatformRegistry

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry, update_env_variable


def prompt_platform_selection(registered_platforms: dict[str, Any]) -> list[str]:
    """Interactive prompt allowing user to select which platform extensions to enable."""
    p_list = list(registered_platforms.values())
    print("\nSelect platform extensions to enable in your vault:")
    for idx, p in enumerate(p_list, start=1):
        print(f"  [{idx}] {p.display_name} ({p.id})")
    print("  [A] All platforms (Default)")

    try:
        choice = input("\nEnter choice [1-5, comma-separated, or Enter for All]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return [p.id for p in p_list]

    if not choice or choice.lower() == "a":
        return [p.id for p in p_list]

    selected_ids = []
    tokens = [t.strip() for t in choice.split(",") if t.strip()]
    for token in tokens:
        if token.isdigit():
            i = int(token) - 1
            if 0 <= i < len(p_list):
                selected_ids.append(p_list[i].id)
        else:
            for p in p_list:
                if token.lower() in [p.id.lower(), p.raw_folder.lower()] or token.lower() in [
                    a.lower() for a in p.aliases
                ]:
                    selected_ids.append(p.id)
                    break

    return selected_ids or [p.id for p in p_list]


def prompt_degiro_portfolio() -> str:
    """Interactive sub-step prompt for Degiro default target portfolio."""
    print("\n  ↳ [Sub-step: Degiro] Select default target portfolio for Degiro positions:")
    print("    [1] Aggressive (Growth equities & thematic ETFs) [Default]")
    print("    [2] Long term  (Core multi-asset & index ETFs)")
    try:
        choice = input("  Enter choice [1-2, or Enter for Aggressive]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "Aggressive"

    if choice in ("2", "long term", "long_term", "long"):
        return "Long term"
    return "Aggressive"


def prompt_exante_mode() -> str:
    """Interactive prompt allowing user to select Exante data import mode (CSV or REST API)."""
    print("\n  ↳ [Sub-step: Exante] Select Exante import mode:")
    print("    [1] CSV Export (Import local statements from 00_Raw/exante/*.csv) [Default]")
    print("    [2] REST API   (Fetch live positions & balances via Exante OpenAPI)")
    try:
        choice = input("\nEnter choice [1-2, 'csv'/'api', or Enter for CSV]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "csv"

    if choice in ("2", "api", "rest", "rest_api"):
        return "api"
    return "csv"


def prompt_exante_api_credentials(env_path: str) -> bool:
    """Optionally prompt user to configure Exante REST API credentials in .env."""
    print("\n  Configure Exante REST API credentials (press Enter to skip and edit .env later):")
    try:
        api_key = input("    EXANTE_API_KEY (Application ID) [Enter to skip]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return False

    if not api_key:
        print(
            "   ℹ️  Skipped Exante API credentials prompt. Remember to set EXANTE_API_KEY & EXANTE_API_SECRET in .env."
        )
        return False

    api_secret = ""
    account_id = ""
    api_url = "https://api-live.exante.eu"

    try:
        api_secret = input("    EXANTE_API_SECRET (Shared Key): ").strip()
        account_id = input("    EXANTE_ACCOUNT_ID (Optional, Enter for auto-discovery): ").strip()
        env_choice = (
            input(
                "    Exante Environment ([1] Live https://api-live.exante.eu [Default], "
                "[2] Demo https://api-demo.exante.eu): "
            )
            .strip()
            .lower()
        )
        if env_choice in ("2", "demo"):
            api_url = "https://api-demo.exante.eu"
    except (EOFError, KeyboardInterrupt):
        pass

    update_env_variable(env_path, "EXANTE_API_KEY", api_key)
    if api_secret:
        update_env_variable(env_path, "EXANTE_API_SECRET", api_secret)
    if account_id:
        update_env_variable(env_path, "EXANTE_ACCOUNT_ID", account_id)
    update_env_variable(env_path, "EXANTE_API_URL", api_url)
    print(f"   ✓ Saved Exante API configuration to .env ({api_url}).")
    return True


def _run_degiro_substep(ctx: InitContext) -> None:
    """Execute Degiro broker configuration sub-step."""
    portfolio = ctx.degiro_portfolio
    if not portfolio:
        portfolio = prompt_degiro_portfolio() if ctx.interactive else "Aggressive"
    ctx.degiro_portfolio = portfolio
    try:
        PlatformRegistry.set_platform_default_portfolio("degiro", portfolio, base_dir=ctx.target_dir)
        print(f"   ✓ Configured Degiro default portfolio: {portfolio}.")
    except Exception:
        pass


def _run_exante_substep(ctx: InitContext) -> None:
    """Execute Exante broker configuration sub-step (CSV vs API mode & credentials)."""
    effective_mode = "csv"
    if ctx.exante_mode and ctx.exante_mode.lower().strip() in ("csv", "api"):
        effective_mode = ctx.exante_mode.lower().strip()
    elif ctx.interactive:
        effective_mode = prompt_exante_mode()

    ctx.exante_mode = effective_mode
    try:
        PlatformRegistry.set_platform_mode("exante", effective_mode, base_dir=ctx.target_dir)
        print(f"   ✓ Configured Exante default import mode: {effective_mode.upper()}.")
    except Exception:
        pass

    if effective_mode == "api" and ctx.interactive:
        env_target = os.path.join(ctx.target_dir, ".env")
        prompt_exante_api_credentials(env_target)


BROKER_SUBSTEPS: dict[str, Callable[[InitContext], None]] = {
    "exante": _run_exante_substep,
}


@InitStepRegistry.register
class BrokersStep(BaseInitStep):
    """Step 2: Select broker platforms and execute per-broker configuration sub-steps."""

    step_id = "brokers"
    step_number = 2
    title = "Configuring broker platforms & per-broker sub-steps"
    description = "Enable broker platforms (PKO BP, mBank IKE/IKZE, Degiro, Exante) and configure broker sub-steps."
    aliases = ["platforms", "broker", "platform"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)

        all_platforms = PlatformRegistry.get_all(base_dir=ctx.target_dir)
        if not ctx.selected_platform_ids:
            ctx.selected_platform_ids = (
                prompt_platform_selection(all_platforms) if ctx.interactive else list(all_platforms.keys())
            )

        # Enable/disable platforms in config.yaml
        for pid in all_platforms:
            is_active = pid in ctx.selected_platform_ids
            try:
                PlatformRegistry.set_platform_enabled(pid, is_active, base_dir=ctx.target_dir)
            except Exception:
                pass

        # Run per-broker sub-steps only for selected platforms
        for pid in ctx.selected_platform_ids:
            substep_fn = BROKER_SUBSTEPS.get(pid)
            if substep_fn:
                substep_fn(ctx)

        # Create raw folders for selected platforms (skipping Exante if configured for API-only)
        for pid in ctx.selected_platform_ids:
            if pid == "exante" and ctx.exante_mode == "api":
                continue
            p = all_platforms.get(pid)
            if p and p.raw_folder:
                dpath = os.path.join(ctx.target_dir, "00_Raw", p.raw_folder)
                os.makedirs(dpath, exist_ok=True)
                gitkeep = os.path.join(dpath, ".gitkeep")
                if not os.path.exists(gitkeep) and not os.listdir(dpath):
                    with open(gitkeep, "w", encoding="utf-8") as f:
                        f.write("")

        print(f"   ✓ Configured {len(ctx.selected_platform_ids)} active broker platform(s) in config.yaml.")
        return True
