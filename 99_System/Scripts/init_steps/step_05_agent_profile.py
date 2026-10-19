"""Step 5: Investor Profile and AI Assistant Configuration."""

import os
import re

from platforms.base import PlatformRegistry

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry, update_env_variable


def _update_user_profile_in_config(
    config_path: str,
    risk_tolerance: str = "moderate",
    tax_sensitive: bool = True,
    max_single_stock_pct: float | None = 15.0,
    allow_profit_harvesting: bool = True,
    tax_advantaged_priority: list[str] | None = None,
) -> None:
    """Update user_profile section in config.yaml preserving existing formatting."""
    if tax_advantaged_priority is None:
        tax_advantaged_priority = ["mbank_ike", "mbank_ikze"]

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    effective_cap = max_single_stock_pct if max_single_stock_pct is not None else 15.0

    if "user_profile:" not in content:
        priority_items = "\n".join(f'    - "{p}"' for p in tax_advantaged_priority)
        profile_block = (
            "\n# Investor Profile & AI Rebalancing Rules of Engagement\n"
            "user_profile:\n"
            f'  risk_tolerance: "{risk_tolerance}"\n'
            f"  max_single_stock_pct: {effective_cap}\n"
            f"  tax_sensitive: {str(tax_sensitive).lower()}\n"
            f"  allow_profit_harvesting: {str(allow_profit_harvesting).lower()}\n"
            "  tax_advantaged_priority:\n"
            f"{priority_items}\n"
        )
        with open(config_path, "a", encoding="utf-8") as f:
            f.write(profile_block)
        return

    content = re.sub(
        r"(?m)^(  risk_tolerance:\s*).*$",
        rf'\g<1>"{risk_tolerance}"',
        content,
    )
    if max_single_stock_pct is not None:
        content = re.sub(
            r"(?m)^(  max_single_stock_pct:\s*).*$",
            rf"\g<1>{max_single_stock_pct}",
            content,
        )
    content = re.sub(
        r"(?m)^(  tax_sensitive:\s*).*$",
        rf"\g<1>{str(tax_sensitive).lower()}",
        content,
    )
    content = re.sub(
        r"(?m)^(  allow_profit_harvesting:\s*).*$",
        rf"\g<1>{str(allow_profit_harvesting).lower()}",
        content,
    )

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)


def prompt_finnhub_api_key(env_path: str) -> bool:
    """Optionally prompt user to configure FINNHUB_API_KEY in .env for AI research & enrichment."""
    print("\n  ↳ [AI & Research Data] Configure Finnhub API Key (optional, used for fundamentals & insider alerts):")
    try:
        api_key = input("    FINNHUB_API_KEY [Enter to skip and configure in .env later]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return False

    if not api_key:
        return False

    update_env_variable(env_path, "FINNHUB_API_KEY", api_key)
    print("   ✓ Saved FINNHUB_API_KEY to .env.")
    return True


def configure_user_profile(
    target_dir: str,
    interactive: bool = True,
    max_single_stock_pct: float | None = None,
    selected_platform_ids: list[str] | None = None,
) -> None:
    """Prompt user for investor risk profile and AI assistant preferences, updating config.yaml."""
    config_path = os.path.join(target_dir, "config.yaml")
    if not os.path.exists(config_path):
        return

    risk_tolerance = "moderate"
    tax_sensitive = True
    allow_profit_harvesting = True

    if interactive:
        print("\nSelect your investment risk tolerance profile for AI Advisor:")
        print("  [1] Conservative (Capital preservation focus, wide corridors, zero speculative trades)")
        print("  [2] Moderate     (Balanced compound growth, disciplined rebalancing) [Default]")
        print("  [3] Aggressive   (Alpha-seeking, higher single-stock volatility, dynamic rebalancing)")
        try:
            r_choice = input("Enter choice [1-3, or Enter for Moderate]: ").strip()
            if r_choice == "1":
                risk_tolerance = "conservative"
            elif r_choice == "3":
                risk_tolerance = "aggressive"
        except (EOFError, KeyboardInterrupt):
            pass

        try:
            tax_choice = (
                input("Prioritize cash-flow DCA over sales to avoid capital gains tax (Belka tax)? [Y/n]: ")
                .strip()
                .lower()
            )
            if tax_choice in ("n", "no"):
                tax_sensitive = False
        except (EOFError, KeyboardInterrupt):
            pass

        try:
            harvest_choice = (
                input(
                    "Allow AI advisor to propose harvesting profits from Aggressive into Long Term core ETFs? [Y/n]: "
                )
                .strip()
                .lower()
            )
            if harvest_choice in ("n", "no"):
                allow_profit_harvesting = False
        except (EOFError, KeyboardInterrupt):
            pass

        env_path = os.path.join(target_dir, ".env")
        if os.path.exists(env_path):
            prompt_finnhub_api_key(env_path)

    # Determine active tax-advantaged accounts
    active_ids = selected_platform_ids
    if not active_ids:
        try:
            active_ids = list(PlatformRegistry.get_enabled(base_dir=target_dir).keys())
        except Exception:
            active_ids = ["mbank_ike", "mbank_ikze"]

    tax_priority: list[str] = [pid for pid in ("mbank_ike", "mbank_ikze") if pid in active_ids]
    if not tax_priority:
        tax_priority = ["mbank_ike", "mbank_ikze"]

    _update_user_profile_in_config(
        config_path,
        risk_tolerance=risk_tolerance,
        tax_sensitive=tax_sensitive,
        max_single_stock_pct=max_single_stock_pct,
        allow_profit_harvesting=allow_profit_harvesting,
        tax_advantaged_priority=tax_priority,
    )
    print(
        f"   ✓ Configured investor & AI profile: {risk_tolerance.capitalize()}, "
        f"Tax-Sensitive: {tax_sensitive}, Profit-Harvesting: {allow_profit_harvesting}."
    )


@InitStepRegistry.register
class AgentProfileStep(BaseInitStep):
    """Step 5: Configure investor profile and AI assistant rules of engagement."""

    step_id = "agent_profile"
    step_number = 5
    title = "Configuring investor profile & AI assistant preferences"
    description = "Set risk tolerance, tax sensitivity, profit harvesting rules, and AI research credentials."
    aliases = ["agent-profile", "user_profile", "user-profile", "profile", "ai", "agents"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)
        configure_user_profile(
            ctx.target_dir,
            interactive=ctx.interactive,
            max_single_stock_pct=ctx.max_single_stock_pct,
            selected_platform_ids=ctx.selected_platform_ids or None,
        )
        return True
