"""Interactive Vault Scaffolding & Initial Setup Engine.

Guides the user step-by-step through configuring a new personal investment vault
bootstrapped from the starter repository.
"""

import os
import shutil
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
from model.config import DEFAULT_CURRENCY_SYMBOLS
from platforms.base import PlatformRegistry


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
            # Match by id or alias
            for p in p_list:
                if token.lower() in [p.id.lower(), p.raw_folder.lower()] or token.lower() in [
                    a.lower() for a in p.aliases
                ]:
                    selected_ids.append(p.id)
                    break

    return selected_ids or [p.id for p in p_list]


def prompt_base_currency_selection(supported_currencies: list[str]) -> tuple[str, str, str]:
    """Interactive prompt allowing user to select base portfolio currency with prefix matching."""
    default_curr = "PLN"
    print("\nSelect base portfolio currency:")
    display_curr_options = ", ".join(supported_currencies)
    print(f"  Supported options: {display_curr_options}")
    print("  Type prefix to quick-select (e.g., 'P' -> PLN, 'E' -> EUR, 'U' -> USD, 'C' -> CHF).")

    try:
        choice = input(f"\nEnter currency choice [or Enter for {default_curr}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if not choice:
        selected = default_curr
    else:
        token = choice.strip().upper()
        if token in supported_currencies:
            selected = token
        else:
            matches = [c for c in supported_currencies if c.upper().startswith(token)]
            if len(matches) == 1:
                selected = matches[0]
                print(f"   ✓ Auto-completed '{choice}' -> {selected}")
            elif len(matches) > 1:
                print(f"Multiple currencies match '{choice}':")
                for idx, m in enumerate(matches, 1):
                    print(f"  [{idx}] {m}")
                try:
                    disambig = input(f"Select choice [1-{len(matches)}, default 1]: ").strip()
                    if disambig.isdigit() and 1 <= int(disambig) <= len(matches):
                        selected = matches[int(disambig) - 1]
                    else:
                        selected = matches[0]
                except (EOFError, KeyboardInterrupt):
                    selected = matches[0]
                print(f"   ✓ Selected {selected}")
            elif len(token) == 3 and token.isalpha():
                selected = token
                print(f"   ✓ Using custom ISO-4217 currency: {selected}")
            else:
                print(f"   ⚠️ Unrecognized input '{choice}'. Defaulting to {default_curr}.")
                selected = default_curr

    if selected in DEFAULT_CURRENCY_SYMBOLS:
        symbol, position = DEFAULT_CURRENCY_SYMBOLS[selected]
    else:
        symbol, position = selected, "suffix"

    return selected, symbol, position


def _update_localization_in_config(
    config_path: str,
    base_currency: str = "PLN",
    currency_symbol: str = "zł",
    symbol_position: str = "suffix",
    supported_currencies: list[str] | None = None,
) -> None:
    """Update or insert localization section in config.yaml preserving formatting."""
    import re

    if supported_currencies is None:
        supported_currencies = ["PLN", "EUR", "USD", "GBP", "CHF"]

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    if "localization:" not in content:
        curr_items = "\n".join(f'    - "{c}"' for c in supported_currencies)
        loc_block = (
            "\n# Localization & Base Currency Configuration\n"
            "localization:\n"
            f'  base_currency: "{base_currency}"\n'
            f'  currency_symbol: "{currency_symbol}"\n'
            f'  symbol_position: "{symbol_position}"\n'
            "  supported_currencies:\n"
            f"{curr_items}\n"
        )
        with open(config_path, "a", encoding="utf-8") as f:
            f.write(loc_block)
        return

    content = re.sub(
        r"(?m)^(  base_currency:\s*).*$",
        rf'\g<1>"{base_currency}"',
        content,
    )
    content = re.sub(
        r"(?m)^(  currency_symbol:\s*).*$",
        rf'\g<1>"{currency_symbol}"',
        content,
    )
    content = re.sub(
        r"(?m)^(  symbol_position:\s*).*$",
        rf'\g<1>"{symbol_position}"',
        content,
    )

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)


def configure_localization(target_dir: str, interactive: bool = True) -> tuple[str, str, str]:
    """Configure base portfolio currency and localization settings in config.yaml."""
    config_path = os.path.join(target_dir, "config.yaml")
    supported = ["PLN", "EUR", "USD", "GBP", "CHF"]

    if not os.path.exists(config_path):
        return "PLN", "zł", "suffix"

    if interactive:
        base_curr, symbol, pos = prompt_base_currency_selection(supported)
    else:
        base_curr, symbol, pos = "PLN", "zł", "suffix"

    _update_localization_in_config(
        config_path,
        base_currency=base_curr,
        currency_symbol=symbol,
        symbol_position=pos,
        supported_currencies=supported,
    )
    print(f"   ✓ Configured base currency: {base_curr} ('{symbol}', {pos}).")
    return base_curr, symbol, pos


def _update_user_profile_in_config(
    config_path: str,
    risk_tolerance: str = "moderate",
    tax_sensitive: bool = True,
    max_single_stock_pct: float = 15.0,
    allow_profit_harvesting: bool = True,
) -> None:
    """Update user_profile section in config.yaml preserving existing formatting."""
    import re

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    if "user_profile:" not in content:
        profile_block = (
            "\n# Investor Profile & AI Rebalancing Rules of Engagement\n"
            "user_profile:\n"
            f'  risk_tolerance: "{risk_tolerance}"\n'
            f"  max_single_stock_pct: {max_single_stock_pct}\n"
            f"  tax_sensitive: {str(tax_sensitive).lower()}\n"
            f"  allow_profit_harvesting: {str(allow_profit_harvesting).lower()}\n"
            "  tax_advantaged_priority:\n"
            '    - "mbank_ike"\n'
            '    - "mbank_ikze"\n'
        )
        with open(config_path, "a", encoding="utf-8") as f:
            f.write(profile_block)
        return

    content = re.sub(
        r"(?m)^(  risk_tolerance:\s*).*$",
        rf'\g<1>"{risk_tolerance}"',
        content,
    )
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


def configure_user_profile(target_dir: str, interactive: bool = True) -> None:
    """Prompt user for risk tolerance and rebalancing rules, updating config.yaml."""
    config_path = os.path.join(target_dir, "config.yaml")
    if not os.path.exists(config_path):
        return

    risk_tolerance = "moderate"
    tax_sensitive = True
    max_single_stock_pct = 15.0
    allow_profit_harvesting = True

    if interactive:
        print("\nSelect your investment risk tolerance profile:")
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
            cap_input = input("Max percentage cap for any single equity position [Enter for 15.0%]: ").strip()
            if cap_input:
                max_single_stock_pct = float(cap_input)
        except (EOFError, KeyboardInterrupt, ValueError):
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

    _update_user_profile_in_config(
        config_path,
        risk_tolerance=risk_tolerance,
        tax_sensitive=tax_sensitive,
        max_single_stock_pct=max_single_stock_pct,
        allow_profit_harvesting=allow_profit_harvesting,
    )
    print(
        f"   ✓ Configured investor profile: {risk_tolerance.capitalize()}, Tax-Sensitive: {tax_sensitive}, Single-Stock Cap: {max_single_stock_pct}%."
    )


def init_vault(
    target_vault: str | None = None,
    interactive: bool = True,
) -> bool:
    """Initialize or configure a vault step-by-step."""
    target_dir = os.path.abspath(target_vault or VAULT_ROOT)

    print("=" * 72)
    print("🚀  INVESTMENT SECOND BRAIN — VAULT INITIALIZER")
    print("=" * 72)
    print(f"📁 Target Vault Directory: {target_dir}")
    print("=" * 72)
    print()

    # 1. Platform Selection & Directory Structure Scaffolding
    print("Step 1: Configuring platform extensions & directory structure...")
    all_platforms = PlatformRegistry.get_all(base_dir=target_dir)

    selected_platform_ids = prompt_platform_selection(all_platforms) if interactive else list(all_platforms.keys())

    # Base directories
    dirs_to_create = [
        "00_Raw/Articles",
        "10_Finance/Assets",
        "10_Finance/ETF_Holdings",
        "10_Finance/History",
        "10_Finance/Watchlist",
        "20_Decisions",
        "99_System/Scripts",
        "99_System/Templates",
        "99_System/Views",
        "99_System/docs",
    ]

    # Add raw directories for enabled platforms
    for pid in selected_platform_ids:
        p = all_platforms.get(pid)
        if p and p.raw_folder:
            dirs_to_create.append(f"00_Raw/{p.raw_folder}")

    for rel_d in dirs_to_create:
        dpath = os.path.join(target_dir, rel_d)
        os.makedirs(dpath, exist_ok=True)
        gitkeep = os.path.join(dpath, ".gitkeep")
        if not os.path.exists(gitkeep) and not os.listdir(dpath):
            with open(gitkeep, "w", encoding="utf-8") as f:
                f.write("")
    print(f"   ✓ Core directories and {len(selected_platform_ids)} platform raw folders created.")

    # 2. Set .vault_version
    print("\nStep 2: Initializing vault version...")
    starter_version_file = os.path.join(VAULT_ROOT, ".vault_version")
    starter_version = "0.6.0"
    if os.path.exists(starter_version_file):
        try:
            with open(starter_version_file, encoding="utf-8") as f:
                starter_version = f.read().strip() or "0.6.0"
        except Exception:
            pass

    target_version_file = os.path.join(target_dir, ".vault_version")
    with open(target_version_file, "w", encoding="utf-8") as f:
        f.write(f"{starter_version}\n")
    print(f"   ✓ Vault version set to v{starter_version}")

    # 3. Environment variables configuration (.env)
    print("\nStep 3: Environment configuration (.env)...")
    env_target = os.path.join(target_dir, ".env")
    env_example = os.path.join(VAULT_ROOT, ".env.example")

    if not os.path.exists(env_target):
        if os.path.exists(env_example):
            shutil.copy2(env_example, env_target)
            print("   ✓ Copied .env.example -> .env")
        else:
            with open(env_target, "w", encoding="utf-8") as f:
                f.write("# Environment Configuration\nFINNHUB_API_KEY=\nEXANTE_API_KEY=\nEXANTE_API_SECRET=\n")
            print("   ✓ Created initial .env file")
    else:
        print("   ✓ Existing .env preserved.")

    # 4. Gitignore configuration
    print("\nStep 4: Ensuring .gitignore configuration...")
    gitignore_target = os.path.join(target_dir, ".gitignore")
    gitignore_source = os.path.join(VAULT_ROOT, ".gitignore")
    if not os.path.exists(gitignore_target) and os.path.exists(gitignore_source):
        shutil.copy2(gitignore_source, gitignore_target)
        print("   ✓ Initialized .gitignore")
    else:
        print("   ✓ .gitignore present.")

    # 5. Core Configuration (config.yaml)
    print("\nStep 5: Verifying config.yaml...")
    config_target = os.path.join(target_dir, "config.yaml")
    config_source = os.path.join(VAULT_ROOT, "config.yaml")
    if not os.path.exists(config_target) and os.path.exists(config_source):
        shutil.copy2(config_source, config_target)
        print("   ✓ Initialized config.yaml")
    else:
        print("   ✓ config.yaml present.")

    # Apply platform choices to config.yaml
    for pid, p in all_platforms.items():
        is_active = pid in selected_platform_ids
        try:
            PlatformRegistry.set_platform_enabled(pid, is_active, base_dir=target_dir)
        except Exception:
            pass
    print("   ✓ Configured platform statuses in config.yaml.")

    # 6. Base Currency & Localization Setup
    print("\nStep 6: Configuring base portfolio currency & localization...")
    configure_localization(target_dir, interactive=interactive)

    # 7. Investor Profile & Rebalancing Setup
    print("\nStep 7: Configuring investor profile & rebalance preferences...")
    configure_user_profile(target_dir, interactive=interactive)

    # 8. Python Environment Diagnostics
    print("\nStep 8: Checking Python dependencies...")
    required_packages = [
        ("requests", "requests"),
        ("yaml", "PyYAML"),
        ("pydantic", "pydantic"),
        ("yfinance", "yfinance"),
        ("bs4", "beautifulsoup4"),
        ("rich", "rich"),
        ("xlrd", "xlrd"),
    ]
    missing = []
    for mod_name, pkg_name in required_packages:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"   ⚠️ Missing Python packages: {', '.join(missing)}")
        print("   Install them using:")
        print(f"   pip install {' '.join(missing)}")
    else:
        print("   ✓ All required core packages are installed.")

    # 9. Integrations Connectivity Diagnostics
    print("\nStep 9: Testing external connectivity & integrations...")
    run_diagnostics = False
    if interactive:
        try:
            choice = (
                input("   Would you like to test external connectivity & integrations now? [Y/n]: ").strip().lower()
            )
            run_diagnostics = choice in ("", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            run_diagnostics = False

    if run_diagnostics:
        from health_check import run_health_check

        try:
            report, _ = run_health_check(
                target_vault=target_dir,
                write_markdown=True,
            )
            print(f"   ✓ Health check completed ({report.passed_count}/{len(report.results)} services OK).")
        except Exception as e:
            print(f"   ⚠️ Health check encountered an error: {e}")
    else:
        print("   Skipped diagnostic check. You can run it anytime with 'python run.py --health'.")

    print("\n" + "=" * 72)
    print("✨ Vault initialization completed successfully!")
    print("=" * 72)
    print("Next steps:")
    active_folders = [all_platforms[pid].raw_folder for pid in selected_platform_ids if pid in all_platforms]
    print(f"  1. Add broker exports to 00_Raw/ ({', '.join(active_folders)}).")
    print("  2. Configure your API keys in .env (Finnhub, Exante).")
    print("  3. Run 'python run.py --health' to inspect your integration diagnostics (Health.md).")
    print("  4. Run 'python run.py --all' to execute your first import & analytics.")
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
        "--non-interactive",
        action="store_true",
        help="Run without prompting.",
    )
    args = parser.parse_args()

    success = init_vault(target_vault=args.target, interactive=not args.non_interactive)
    sys.exit(0 if success else 1)
