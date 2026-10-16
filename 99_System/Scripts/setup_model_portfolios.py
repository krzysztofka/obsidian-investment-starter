"""Interactive Model Portfolio Setup & Target Corridors CLI.

Allows the user to interactively configure model portfolio allocation targets,
tolerance corridor margins, and rebalancing strategies across sub-portfolios
(Safety Net, Long Term, Aggressive, or custom buckets).

Usage:
  python 99_System/Scripts/setup_model_portfolios.py
  python run.py --setup-model-portfolios
  python 99_System/Scripts/setup_model_portfolios.py --target /path/to/vault
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

# Ensure scripts root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = SCRIPT_DIR
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, SCRIPTS_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import yaml
from model.config import load_vault_config

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
    console: Any = Console()
except ImportError:
    HAS_RICH = False
    console = None


STANDARD_PORTFOLIOS = {
    "safety_net": "Safety net",
    "long_term": "Long term",
    "aggressive": "Aggressive",
}

DEFAULT_ASSET_CLASSES = ["Equities", "Bonds", "Cash", "Real Estate", "Commodities", "Crypto"]
DEFAULT_SECTORS = [
    "Technology",
    "Military",
    "Finance",
    "Healthcare",
    "Real Estate",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Industrials",
    "Energy",
    "Basic Materials",
    "Cash",
]


def discover_vault_assets_for_portfolio(vault_root: str, portfolio_name: str) -> list[str]:
    """Scan 10_Finance/Assets/ for asset notes tagged with given portfolio."""
    assets_dir = os.path.join(vault_root, "10_Finance", "Assets")
    if not os.path.exists(assets_dir):
        return ["Cash"]

    discovered: list[str] = []
    norm_target = portfolio_name.lower().replace(" ", "").replace("_", "").replace("-", "")

    for fname in sorted(os.listdir(assets_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(assets_dir, fname)
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Quick parse frontmatter
            match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not match:
                continue

            fm = yaml.safe_load(match.group(1))
            if not isinstance(fm, dict):
                continue

            port = str(fm.get("portfolio") or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            if port == norm_target:
                ticker = fm.get("ticker")
                name = fm.get("name")
                item = str(ticker or name or os.path.splitext(fname)[0]).strip()
                if item and item not in discovered:
                    discovered.append(item)
        except Exception:
            continue

    if "Cash" not in discovered:
        discovered.append("Cash")

    return discovered


def load_model_portfolios_raw(config_path: str) -> dict[str, Any]:
    """Load the model_portfolios dict from config.yaml, or return defaults if absent."""
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        if isinstance(cfg, dict) and "model_portfolios" in cfg:
            mp = cfg.get("model_portfolios")
            return dict(mp) if isinstance(mp, dict) else {}
    except Exception:
        pass

    return {}


def format_model_portfolios_yaml(model_portfolios_data: dict[str, Any]) -> str:
    """Format model_portfolios data into clean, readable YAML block."""
    lines = [
        "# Model Portfolios & Rebalancing Configuration",
        "model_portfolios:",
    ]

    for pkey, pcfg in model_portfolios_data.items():
        lines.append(f"  {pkey}:")
        name = pcfg.get("name", pkey.capitalize())
        lines.append(f'    name: "{name}"')
        strat = pcfg.get("rebalance_strategy", "inflow_first")
        lines.append(f'    rebalance_strategy: "{strat}"')
        tol = float(pcfg.get("tolerance_band_pct", 5.0))
        lines.append(f"    tolerance_band_pct: {tol:.1f}")
        min_trade = float(pcfg.get("min_trade_amount_pln", 500.0))
        lines.append(f"    min_trade_amount_pln: {min_trade:.1f}")
        pri_layer = pcfg.get("primary_layer", "asset_classes")
        lines.append(f'    primary_layer: "{pri_layer}"')

        layers = pcfg.get("layers", {})
        if isinstance(layers, dict) and layers:
            lines.append("    layers:")
            for lname, items in layers.items():
                if not isinstance(items, list) or not items:
                    continue
                lines.append(f"      {lname}:")
                for it in items:
                    t_name = it.get("target", "")
                    w_pct = float(it.get("weight_pct", 0.0))
                    lines.append(f'        - target: "{t_name}"')
                    lines.append(f"          weight_pct: {w_pct:.1f}")
                    if it.get("tolerance_band_pct") is not None:
                        t_band = float(it["tolerance_band_pct"])
                        lines.append(f"          tolerance_band_pct: {t_band:.1f}")
                    if it.get("min_trade_amount_pln") is not None:
                        t_min = float(it["min_trade_amount_pln"])
                        lines.append(f"          min_trade_amount_pln: {t_min:.1f}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_model_portfolios_to_config(config_path: str, model_portfolios_data: dict[str, Any]) -> None:
    """Non-destructively replace or append model_portfolios in config.yaml."""
    yaml_block = format_model_portfolios_yaml(model_portfolios_data)

    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(yaml_block)
        return

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    # Check if model_portfolios section already exists
    pattern = re.compile(
        r"(?m)^(?:\s*#.*?\n)*\s*model_portfolios:\s*\n(?:[ \t]+.*?\n|\s*\n)*(?=^[a-zA-Z0-9_-]+:|\Z)",
        re.MULTILINE,
    )

    if pattern.search(content):
        new_content = pattern.sub(yaml_block + "\n", content, count=1)
    else:
        # Insert before user_profile: if found, else append to bottom
        user_prof_match = re.search(r"(?m)^(?:\s*#.*?\n)*\s*user_profile:", content)
        if user_prof_match:
            idx = user_prof_match.start()
            new_content = content[:idx] + yaml_block + "\n" + content[idx:]
        else:
            new_content = content.rstrip() + "\n\n" + yaml_block

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def prompt_string(prompt_text: str, default: str | None = None) -> str:
    """Prompt user for a string with optional default."""
    if default is not None:
        p_str = f"{prompt_text} [{default}]: "
    else:
        p_str = f"{prompt_text}: "

    try:
        val = input(p_str).strip()
    except (EOFError, KeyboardInterrupt):
        return default or ""

    return val if val else (default or "")


def prompt_float(prompt_text: str, default: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Prompt user for a float within range [min_val, max_val]."""
    while True:
        p_str = f"{prompt_text} [Enter for {default}]: "
        try:
            val_str = input(p_str).strip()
        except (EOFError, KeyboardInterrupt):
            return default

        if not val_str:
            return default

        try:
            val = float(val_str)
            if min_val <= val <= max_val:
                return val
            print(f"   ⚠️ Value must be between {min_val} and {max_val}.")
        except ValueError:
            print("   ⚠️ Please enter a valid numeric value.")


def display_model_portfolios_summary(model_portfolios: dict[str, Any]) -> None:
    """Display a clean summary table of existing model portfolios."""
    if not model_portfolios:
        print("\nℹ️ No model portfolios currently configured in config.yaml.")
        return

    if HAS_RICH and console:
        table = Table(title="📊 Configured Model Portfolios", show_header=True, header_style="bold cyan")
        table.add_column("Bucket Key", style="dim")
        table.add_column("Display Name", style="bold")
        table.add_column("Strategy")
        table.add_column("Corridor Margin")
        table.add_column("Min Trade")
        table.add_column("Primary Layer")
        table.add_column("Targets Breakdown", style="green")

        for key, pcfg in model_portfolios.items():
            name = pcfg.get("name", key)
            strat = pcfg.get("rebalance_strategy", "inflow_first")
            tol = f"±{pcfg.get('tolerance_band_pct', 5.0)}%"
            min_tr = f"{pcfg.get('min_trade_amount_pln', 500.0)} PLN"
            pri_layer = pcfg.get("primary_layer", "asset_classes")

            items = pcfg.get("layers", {}).get(pri_layer, [])
            targets_str = ", ".join(f"{it.get('target')}: {it.get('weight_pct')}%" for it in items) or "None"

            table.add_row(key, name, strat, tol, min_tr, pri_layer, targets_str)

        console.print(table)
    else:
        print("\n=== Configured Model Portfolios ===")
        for key, pcfg in model_portfolios.items():
            name = pcfg.get("name", key)
            strat = pcfg.get("rebalance_strategy", "inflow_first")
            tol = pcfg.get("tolerance_band_pct", 5.0)
            pri = pcfg.get("primary_layer", "asset_classes")
            items = pcfg.get("layers", {}).get(pri, [])
            items_str = ", ".join(f"{it.get('target')}: {it.get('weight_pct')}%" for it in items)
            print(f"• {name} ({key}): {strat} | Margin ±{tol}% | Layer: {pri} | {items_str}")
        print()


def display_layer_targets_table(targets: list[dict[str, Any]], default_tol: float, default_min_trade: float) -> None:
    """Display table of current targets within a layer and running sum."""
    total_weight = sum(float(it.get("weight_pct", 0.0)) for it in targets)
    rem = max(0.0, 100.0 - total_weight)

    if HAS_RICH and console:
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Target (Asset / Class / Sector)", style="bold")
        table.add_column("Target Weight %", justify="right")
        table.add_column("Tolerance Corridor Margin", justify="right")
        table.add_column("Min Trade (PLN)", justify="right")

        for idx, it in enumerate(targets, start=1):
            t_name = it.get("target", "")
            w_pct = f"{float(it.get('weight_pct', 0.0)):.1f}%"
            tol = (
                f"±{float(it['tolerance_band_pct']):.1f}%"
                if it.get("tolerance_band_pct") is not None
                else f"±{default_tol:.1f}% (default)"
            )
            min_tr = (
                f"{float(it['min_trade_amount_pln']):.1f}"
                if it.get("min_trade_amount_pln") is not None
                else f"{default_min_trade:.1f} (default)"
            )
            table.add_row(str(idx), t_name, w_pct, tol, min_tr)

        console.print(table)
        status_color = "green" if abs(total_weight - 100.0) < 0.01 else ("yellow" if total_weight < 100 else "red")
        console.print(
            f"[{status_color}]Running Total: {total_weight:.1f}% / 100.0% (Remaining: {rem:.1f}%)[/{status_color}]\n"
        )
    else:
        print("\nCurrent Targets:")
        for idx, it in enumerate(targets, start=1):
            tol = f"±{it.get('tolerance_band_pct')}%" if it.get("tolerance_band_pct") else f"±{default_tol}%"
            print(f"  [{idx}] {it.get('target')}: {it.get('weight_pct')}% (Margin: {tol})")
        print(f"Running Total: {total_weight:.1f}% / 100.0% (Remaining: {rem:.1f}%)\n")


def configure_layer_targets_interactively(
    vault_root: str,
    portfolio_name: str,
    layer_name: str,
    default_tolerance: float,
    default_min_trade: float,
    existing_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Interactive loop to add, edit, or delete target allocation items."""
    targets = [dict(it) for it in existing_items]

    # Gather candidate suggestions based on layer type
    if layer_name == "assets":
        candidates = discover_vault_assets_for_portfolio(vault_root, portfolio_name)
    elif layer_name == "sectors":
        candidates = list(DEFAULT_SECTORS)
    else:
        candidates = list(DEFAULT_ASSET_CLASSES)

    while True:
        display_layer_targets_table(targets, default_tolerance, default_min_trade)
        total_w = sum(float(it.get("weight_pct", 0.0)) for it in targets)

        print("Actions:")
        print("  [A] Add new target")
        if targets:
            print("  [E] Edit existing target")
            print("  [D] Delete target")
            print("  [C] Clear all targets")
        print("  [F] Finish layer setup")

        choice = prompt_string("\nChoose action [A/E/D/C/F]", default="F" if abs(total_w - 100.0) < 0.01 else "A")
        choice_up = choice.upper()

        if choice_up == "A":
            # Add target
            print("\nAvailable / Suggested targets:")
            # Filter out already added items
            current_names = {it.get("target") for it in targets}
            avail = [c for c in candidates if c not in current_names]
            for idx, c in enumerate(avail, start=1):
                print(f"  [{idx}] {c}")
            print("  [O] Other / Custom (type any name or ticker)")

            sel = prompt_string("Select target [number or type name]").strip()
            chosen_target = ""
            if sel.isdigit():
                i = int(sel) - 1
                if 0 <= i < len(avail):
                    chosen_target = avail[i]
            if not chosen_target:
                chosen_target = sel if sel and sel.upper() != "O" else prompt_string("Enter target name / ticker")

            if not chosen_target:
                print("   ⚠️ Target name cannot be empty.")
                continue

            # Weight pct
            remaining = max(0.0, 100.0 - total_w)
            default_w = remaining if remaining > 0 else 10.0
            weight = prompt_float(
                f"Enter target weight percentage for '{chosen_target}' (%)",
                default=round(default_w, 1),
                min_val=0.1,
                max_val=100.0,
            )

            # Optional custom margin override
            override_margin = prompt_string(
                f"Custom tolerance margin % (or press Enter to keep default ±{default_tolerance}%)",
                default="",
            )
            tol_val = None
            if override_margin:
                try:
                    tol_val = float(override_margin)
                except ValueError:
                    tol_val = None

            # Optional custom min trade amount override
            override_min = prompt_string(
                f"Custom min trade PLN (or press Enter to keep default {default_min_trade} PLN)",
                default="",
            )
            min_val = None
            if override_min:
                try:
                    min_val = float(override_min)
                except ValueError:
                    min_val = None

            new_item: dict[str, Any] = {
                "target": chosen_target,
                "weight_pct": weight,
            }
            if tol_val is not None:
                new_item["tolerance_band_pct"] = tol_val
            if min_val is not None:
                new_item["min_trade_amount_pln"] = min_val

            targets.append(new_item)
            print(f"   ✓ Added target '{chosen_target}' ({weight}%).")

        elif choice_up == "E" and targets:
            idx_str = prompt_string(f"Enter target # to edit [1-{len(targets)}]", default="1")
            if idx_str.isdigit() and 1 <= int(idx_str) <= len(targets):
                idx = int(idx_str) - 1
                item = targets[idx]
                curr_w = float(item.get("weight_pct", 0.0))
                new_w = prompt_float(
                    f"New weight percentage for '{item.get('target')}'",
                    default=curr_w,
                    min_val=0.1,
                    max_val=100.0,
                )
                item["weight_pct"] = new_w
                print(f"   ✓ Updated '{item.get('target')}' to {new_w}%.")

        elif choice_up == "D" and targets:
            idx_str = prompt_string(f"Enter target # to delete [1-{len(targets)}]", default="1")
            if idx_str.isdigit() and 1 <= int(idx_str) <= len(targets):
                idx = int(idx_str) - 1
                removed = targets.pop(idx)
                print(f"   ✓ Removed '{removed.get('target')}'.")

        elif choice_up == "C" and targets:
            confirm = prompt_string("Are you sure you want to clear all targets? [y/N]", default="N")
            if confirm.lower() in ("y", "yes"):
                targets.clear()
                print("   ✓ Cleared all targets.")

        elif choice_up == "F":
            # Validation check
            current_sum = sum(float(it.get("weight_pct", 0.0)) for it in targets)
            if abs(current_sum - 100.0) < 0.1:
                return targets

            if current_sum < 100.0:
                diff = round(100.0 - current_sum, 1)
                auto_cash = prompt_string(
                    f"Current total is {current_sum:.1f}% ({diff:.1f}% remaining). Allocate remainder to 'Cash'? [Y/n]",
                    default="Y",
                )
                if auto_cash.lower() in ("y", "yes"):
                    cash_item = next((it for it in targets if it.get("target") == "Cash"), None)
                    if cash_item:
                        cash_item["weight_pct"] = round(float(cash_item["weight_pct"]) + diff, 1)
                    else:
                        targets.append({"target": "Cash", "weight_pct": diff})
                    print(f"   ✓ Added/adjusted 'Cash' to absorb remaining {diff}%.")
                    return targets
                else:
                    print("   ⚠️ Targets must sum to 100.0% before finishing.")
            else:
                diff = round(current_sum - 100.0, 1)
                print(f"   ❌ Total weight exceeds 100% by {diff}%. Please edit or delete items.")


def configure_portfolio_interactively(
    vault_root: str,
    portfolio_key: str,
    existing_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Interactively configure a single model portfolio bucket."""
    cfg = dict(existing_cfg)
    default_name = STANDARD_PORTFOLIOS.get(portfolio_key, portfolio_key.replace("_", " ").capitalize())
    display_name = prompt_string("Portfolio Display Name", default=cfg.get("name", default_name))
    cfg["name"] = display_name

    # 1. Rebalance Strategy
    print("\nRebalancing Strategy Preference:")
    print("  [1] Inflow-First (Direct cash-flow DCA to underweight assets, minimize capital gains tax) [Default]")
    print("  [2] Full Rebalance (Active rebalancing via trimming overweight assets and buying underweight)")
    strat_choice = prompt_string(
        "Choose strategy [1/2]",
        default="1" if cfg.get("rebalance_strategy", "inflow_first") == "inflow_first" else "2",
    )
    cfg["rebalance_strategy"] = "full_rebalance" if strat_choice == "2" else "inflow_first"

    # 2. Portfolio-level Tolerance Corridor Margin
    tol_default = float(cfg.get("tolerance_band_pct", 5.0))
    cfg["tolerance_band_pct"] = prompt_float(
        "Tolerance corridor margin (±% threshold before triggering rebalance drift alert)",
        default=tol_default,
        min_val=0.5,
        max_val=25.0,
    )

    # 3. Minimum Trade Amount
    min_trade_default = float(cfg.get("min_trade_amount_pln", 500.0))
    cfg["min_trade_amount_pln"] = prompt_float(
        "Minimum trade threshold in PLN (to eliminate fee-inefficient micro-transactions)",
        default=min_trade_default,
        min_val=50.0,
        max_val=100000.0,
    )

    # 4. Primary Allocation Layer
    print("\nSelect Primary Allocation Layer:")
    print("  [1] Asset Classes (e.g. Equities, Bonds, Cash) [Default]")
    print("  [2] Specific Assets / Tickers (e.g. MSFT, NVDA, Cash)")
    print("  [3] Dominant Sectors (e.g. Technology, Military, Finance, Cash)")
    layer_map = {"1": "asset_classes", "2": "assets", "3": "sectors"}
    curr_layer = cfg.get("primary_layer", "asset_classes")
    default_layer_num = "1"
    for k, v in layer_map.items():
        if v == curr_layer:
            default_layer_num = k
            break

    layer_choice = prompt_string("Choose primary layer [1/2/3]", default=default_layer_num)
    chosen_layer = layer_map.get(layer_choice, "asset_classes")
    cfg["primary_layer"] = chosen_layer

    # 5. Layer Target Items
    print(f"\n--- Setting Target Breakdown for Layer: {chosen_layer.upper()} ---")
    layers = cfg.setdefault("layers", {})
    existing_items = layers.get(chosen_layer, [])
    new_items = configure_layer_targets_interactively(
        vault_root=vault_root,
        portfolio_name=display_name,
        layer_name=chosen_layer,
        default_tolerance=cfg["tolerance_band_pct"],
        default_min_trade=cfg["min_trade_amount_pln"],
        existing_items=existing_items,
    )
    layers[chosen_layer] = new_items

    return cfg


def interactive_main(vault_root: str | None = None) -> int:
    """Run interactive CLI to setup and customize model portfolios in config.yaml."""
    target_dir = os.path.abspath(vault_root or VAULT_ROOT)
    config_path = os.path.join(target_dir, "config.yaml")

    if HAS_RICH and console:
        console.print(
            Panel.fit(
                f"[bold cyan]🎯 Interactive Model Portfolio & Allocation Targets Setup[/bold cyan]\n"
                f"[dim]Vault Root: {target_dir}[/dim]\n"
                f"Configure target weights, corridor margins, and rebalance strategies.",
                border_style="cyan",
            )
        )
    else:
        print("=" * 72)
        print("🎯  INTERACTIVE MODEL PORTFOLIO SETUP")
        print("=" * 72)
        print(f"📁 Vault Root: {target_dir}")
        print("=" * 72)

    model_portfolios = load_model_portfolios_raw(config_path)

    # If model_portfolios is completely empty, initialize standard presets
    if not model_portfolios:
        model_portfolios = {
            "safety_net": {
                "name": "Safety net",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount_pln": 500.0,
                "primary_layer": "asset_classes",
                "layers": {
                    "asset_classes": [
                        {"target": "Bonds", "weight_pct": 80.0},
                        {"target": "Cash", "weight_pct": 20.0},
                    ]
                },
            },
            "long_term": {
                "name": "Long term",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount_pln": 1000.0,
                "primary_layer": "asset_classes",
                "layers": {
                    "asset_classes": [
                        {"target": "Equities", "weight_pct": 80.0},
                        {"target": "Bonds", "weight_pct": 20.0},
                    ]
                },
            },
            "aggressive": {
                "name": "Aggressive",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount_pln": 500.0,
                "primary_layer": "asset_classes",
                "layers": {
                    "asset_classes": [
                        {"target": "Equities", "weight_pct": 90.0},
                        {"target": "Cash", "weight_pct": 10.0},
                    ]
                },
            },
        }

    while True:
        display_model_portfolios_summary(model_portfolios)

        print("\nSelect an action:")
        print("  [1] Safety Net (safety_net)")
        print("  [2] Long Term (long_term)")
        print("  [3] Aggressive (aggressive)")
        print("  [4] Add or edit custom portfolio bucket")
        print("  [S] Save changes to config.yaml and Exit")
        print("  [Q] Discard / Quit without saving")

        action = prompt_string("\nChoose option [1/2/3/4/S/Q]", default="S").upper()

        if action == "1":
            model_portfolios["safety_net"] = configure_portfolio_interactively(
                target_dir, "safety_net", model_portfolios.get("safety_net", {})
            )
        elif action == "2":
            model_portfolios["long_term"] = configure_portfolio_interactively(
                target_dir, "long_term", model_portfolios.get("long_term", {})
            )
        elif action == "3":
            model_portfolios["aggressive"] = configure_portfolio_interactively(
                target_dir, "aggressive", model_portfolios.get("aggressive", {})
            )
        elif action == "4":
            pkey = prompt_string("Enter new or existing portfolio key (e.g. 'crypto' or 'speculative')")
            if pkey:
                clean_key = re.sub(r"[^a-zA-Z0-9_-]", "_", pkey.strip().lower())
                model_portfolios[clean_key] = configure_portfolio_interactively(
                    target_dir, clean_key, model_portfolios.get(clean_key, {})
                )
        elif action == "S":
            # Validation check via Pydantic model
            try:
                # Save first to config
                save_model_portfolios_to_config(config_path, model_portfolios)
                # Verify that config parses without error
                load_vault_config(base_dir=target_dir, force_refresh=True)
                print(f"\n✨ Successfully updated model portfolio configuration in '{config_path}'!")
                return 0
            except Exception as e:
                print(f"\n❌ Validation error while saving config: {e}")
                retry = prompt_string("Keep editing? [Y/n]", default="Y")
                if retry.lower() not in ("y", "yes"):
                    return 1
        elif action == "Q":
            print("\nExiting without saving.")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive Model Portfolio Setup & Target Corridors CLI.")
    parser.add_argument("--target", default=None, help="Target vault root directory (default: current vault).")
    args = parser.parse_args()

    return interactive_main(vault_root=args.target)


if __name__ == "__main__":
    sys.exit(main())
