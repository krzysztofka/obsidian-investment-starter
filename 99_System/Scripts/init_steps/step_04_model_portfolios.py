"""Step 4: Model Portfolios Preset Selection and Single-Stock Concentration Cap."""

import os
import re
from typing import Any

from model.config import load_vault_config

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry

MODEL_PORTFOLIO_PRESETS: dict[str, dict[str, Any]] = {
    "balanced": {
        "label": "Balanced Multi-Asset (Default)",
        "summary": (
            "Safety Net: 80% Bonds / 20% Cash | "
            "Long Term: 52% Equities / 30% Real Estate / 13% Bonds / 5% Gold | "
            "Aggressive: 90% Equities / 10% Cash"
        ),
        "portfolios": {
            "safety_net": {
                "name": "Safety net",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Bonds", 80.0),
                    ("Cash", 20.0),
                ],
            },
            "long_term": {
                "name": "Long term",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 1000.0,
                "asset_classes": [
                    ("Equities", 52.0),
                    ("Real Estate", 30.0),
                    ("Bonds", 13.0),
                    ("Gold", 5.0),
                ],
            },
            "aggressive": {
                "name": "Aggressive",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Equities", 90.0),
                    ("Cash", 10.0),
                ],
            },
        },
    },
    "conservative": {
        "label": "Conservative Multi-Asset",
        "summary": (
            "Safety Net: 70% Bonds / 30% Cash | "
            "Long Term: 39% Equities / 30% Real Estate / 26% Bonds / 5% Gold | "
            "Aggressive: 80% Equities / 20% Cash"
        ),
        "portfolios": {
            "safety_net": {
                "name": "Safety net",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Bonds", 70.0),
                    ("Cash", 30.0),
                ],
            },
            "long_term": {
                "name": "Long term",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 1000.0,
                "asset_classes": [
                    ("Equities", 39.0),
                    ("Real Estate", 30.0),
                    ("Bonds", 26.0),
                    ("Gold", 5.0),
                ],
            },
            "aggressive": {
                "name": "Aggressive",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Equities", 80.0),
                    ("Cash", 20.0),
                ],
            },
        },
    },
    "aggressive_growth": {
        "label": "Aggressive Growth Multi-Asset",
        "summary": (
            "Safety Net: 85% Bonds / 15% Cash | "
            "Long Term: 58.5% Equities / 30% Real Estate / 6.5% Bonds / 5% Gold | "
            "Aggressive: 100% Equities"
        ),
        "portfolios": {
            "safety_net": {
                "name": "Safety net",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Bonds", 85.0),
                    ("Cash", 15.0),
                ],
            },
            "long_term": {
                "name": "Long term",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 1000.0,
                "asset_classes": [
                    ("Equities", 58.5),
                    ("Real Estate", 30.0),
                    ("Bonds", 6.5),
                    ("Gold", 5.0),
                ],
            },
            "aggressive": {
                "name": "Aggressive",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Equities", 100.0),
                ],
            },
        },
    },
    "classic": {
        "label": "Classic Financial Only (No Real Estate / Gold)",
        "summary": (
            "Safety Net: 80% Bonds / 20% Cash | "
            "Long Term: 80% Equities / 20% Bonds | "
            "Aggressive: 90% Equities / 10% Cash"
        ),
        "portfolios": {
            "safety_net": {
                "name": "Safety net",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Bonds", 80.0),
                    ("Cash", 20.0),
                ],
            },
            "long_term": {
                "name": "Long term",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 1000.0,
                "asset_classes": [
                    ("Equities", 80.0),
                    ("Bonds", 20.0),
                ],
            },
            "aggressive": {
                "name": "Aggressive",
                "rebalance_strategy": "inflow_first",
                "tolerance_band_pct": 5.0,
                "min_trade_amount": 500.0,
                "asset_classes": [
                    ("Equities", 90.0),
                    ("Cash", 10.0),
                ],
            },
        },
    },
}


def prompt_model_portfolio_preset() -> str:
    """Interactive prompt for selecting a model portfolio target allocation preset."""
    preset_keys = ["balanced", "conservative", "aggressive_growth", "classic"]
    print("\nSelect Model Portfolio target allocation preset:")
    for idx, key in enumerate(preset_keys, start=1):
        preset = MODEL_PORTFOLIO_PRESETS[key]
        print(f"  [{idx}] {preset['label']}")
        print(f"      {preset['summary']}")

    try:
        choice = input("\nEnter choice [1-4, or Enter for Balanced Multi-Asset]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "balanced"

    if choice in ("2", "conservative"):
        return "conservative"
    if choice in ("3", "aggressive", "aggressive_growth", "growth"):
        return "aggressive_growth"
    if choice in ("4", "classic"):
        return "classic"
    return "balanced"


def prompt_max_single_stock_pct(default_pct: float = 15.0) -> float:
    """Interactive prompt for maximum single equity position concentration cap."""
    try:
        cap_input = input(f"\nMax percentage cap for any single equity position [Enter for {default_pct}%]: ").strip()
        if cap_input:
            val = float(cap_input)
            if 1.0 <= val <= 100.0:
                return val
            print(f"   ⚠️ Value must be between 1.0% and 100.0%. Using default {default_pct}%.")
    except (EOFError, KeyboardInterrupt, ValueError):
        pass
    return default_pct


def _render_model_portfolios_yaml(preset_id: str) -> str:
    """Render YAML block for model_portfolios from preset definition."""
    preset = MODEL_PORTFOLIO_PRESETS.get(preset_id, MODEL_PORTFOLIO_PRESETS["balanced"])
    lines = ["model_portfolios:\n"]
    for p_key, p_cfg in preset["portfolios"].items():
        lines.append(f"  {p_key}:\n")
        lines.append(f'    name: "{p_cfg["name"]}"\n')
        lines.append(f'    rebalance_strategy: "{p_cfg["rebalance_strategy"]}"\n')
        lines.append(f"    tolerance_band_pct: {p_cfg['tolerance_band_pct']}\n")
        lines.append(f"    min_trade_amount: {p_cfg['min_trade_amount']}\n")
        lines.append('    primary_layer: "asset_classes"\n')
        lines.append("    layers:\n")
        lines.append("      asset_classes:\n")
        for target_name, weight_pct in p_cfg["asset_classes"]:
            lines.append(f'        - target: "{target_name}"\n')
            lines.append(f"          weight_pct: {weight_pct}\n")
        lines.append("\n")
    return "".join(lines)


def _update_model_portfolios_in_config(config_path: str, preset_id: str) -> None:
    """Update or insert model_portfolios section in config.yaml."""
    if not os.path.exists(config_path):
        return

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    new_block = _render_model_portfolios_yaml(preset_id)

    if "model_portfolios:" not in content:
        if content and not content.endswith("\n"):
            content += "\n"
        content += "\n# Model Portfolios & Rebalancing Configuration\n" + new_block
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        return

    lines = content.splitlines(keepends=True)
    new_lines: list[str] = []
    in_model_portfolios = False
    replaced = False

    for line in lines:
        stripped = line.strip()
        if line.startswith("model_portfolios:"):
            in_model_portfolios = True
            new_lines.append(new_block)
            replaced = True
            continue

        if in_model_portfolios:
            # Top-level key or top-level section comment starts
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_model_portfolios = False
                new_lines.append(line)
            continue

        new_lines.append(line)

    if not replaced:
        new_lines.append("\n" + new_block)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write("".join(new_lines))


def _update_single_stock_cap_in_config(config_path: str, max_single_stock_pct: float = 15.0) -> None:
    """Synchronize single-stock concentration cap across user_profile and alerts.allocation_drift."""
    if not os.path.exists(config_path):
        return

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    # 1. Update user_profile.max_single_stock_pct if present
    if re.search(r"(?m)^  max_single_stock_pct:\s*", content):
        content = re.sub(
            r"(?m)^(  max_single_stock_pct:\s*).*$",
            rf"\g<1>{max_single_stock_pct}",
            content,
        )

    # 2. Update alerts.allocation_drift.max_portfolio_weight_pct if present
    if re.search(r"(?m)^    max_portfolio_weight_pct:\s*", content):
        content = re.sub(
            r"(?m)^(    max_portfolio_weight_pct:\s*).*$",
            rf"\g<1>{max_single_stock_pct}",
            content,
        )

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)


def configure_model_portfolios(
    target_dir: str,
    interactive: bool = True,
    preset_id: str | None = None,
    max_single_stock_pct: float | None = None,
) -> tuple[str, float]:
    """Configure model portfolio presets and single-stock concentration cap in config.yaml."""
    config_path = os.path.join(target_dir, "config.yaml")
    selected_preset = preset_id or ("balanced" if interactive else "balanced")
    cap_pct = max_single_stock_pct if max_single_stock_pct is not None else 15.0

    if not os.path.exists(config_path):
        return selected_preset, cap_pct

    if interactive:
        if preset_id is None:
            selected_preset = prompt_model_portfolio_preset()
        if max_single_stock_pct is None:
            cap_pct = prompt_max_single_stock_pct(default_pct=cap_pct)

    _update_model_portfolios_in_config(config_path, selected_preset)
    _update_single_stock_cap_in_config(config_path, cap_pct)
    load_vault_config(base_dir=target_dir, force_refresh=True)

    preset_label = MODEL_PORTFOLIO_PRESETS.get(selected_preset, MODEL_PORTFOLIO_PRESETS["balanced"])["label"]
    print(f"   ✓ Configured model portfolios preset: {preset_label} (Single-Stock Cap: {cap_pct}%).")
    return selected_preset, cap_pct


@InitStepRegistry.register
class ModelPortfoliosStep(BaseInitStep):
    """Step 4: Configure model portfolio presets and single-stock concentration cap."""

    step_id = "model_portfolios"
    step_number = 4
    title = "Configuring model portfolios & concentration limits"
    description = "Select model portfolio allocation presets (including Real Estate & Gold) and single-stock cap."
    aliases = ["model-portfolios", "portfolios", "models", "allocations"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)
        preset, cap = configure_model_portfolios(
            ctx.target_dir,
            interactive=ctx.interactive,
            preset_id=ctx.preset_id,
            max_single_stock_pct=ctx.max_single_stock_pct if not ctx.interactive else None,
        )
        ctx.preset_id = preset
        ctx.max_single_stock_pct = cap
        return True
