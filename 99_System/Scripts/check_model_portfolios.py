"""Model Portfolio Drift Evaluation Engine.

Evaluates portfolio buckets against their configured Model Portfolio targets and
Tolerance Corridors in config.yaml, emitting portfolio-level WARN alerts when
a configured Target Allocation breaches its Tolerance Corridor and meets the
minimum trade threshold.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

# Configure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from model.asset import Asset
from model.config import (
    LocalizationConfig,
    ModelPortfolioConfig,
    ModelPortfolioTargetItem,
    VaultConfig,
    load_vault_config,
)


class TargetDriftStatus(str, Enum):
    """Status of an individual Target Allocation relative to its Tolerance Corridor."""

    BALANCED = "BALANCED"
    OVERWEIGHT = "OVERWEIGHT"
    UNDERWEIGHT = "UNDERWEIGHT"
    BELOW_MIN_TRADE = "BELOW_MIN_TRADE"


@dataclass
class TargetDriftResult:
    """Evaluation result for a single configured Target Allocation."""

    target: str
    actual_value_base: float
    actual_weight_pct: float
    target_weight_pct: float
    tolerance_band_pct: float
    lower_bound_pct: float
    upper_bound_pct: float
    drift_pct: float
    corridor_breach_pct: float
    delta_base: float
    min_trade_amount: float
    is_actionable_breach: bool
    status: TargetDriftStatus


@dataclass
class LayerDriftReport:
    """Evaluation report for a single Allocation Layer within a Model Portfolio."""

    layer_name: str
    is_primary: bool
    targets: list[TargetDriftResult] = field(default_factory=list)

    @property
    def actionable_breaches(self) -> list[TargetDriftResult]:
        return [t for t in self.targets if t.is_actionable_breach]


@dataclass
class PortfolioDriftReport:
    """Evaluation report for a single portfolio bucket."""

    portfolio_key: str
    portfolio_name: str
    rebalance_strategy: str
    primary_layer: str
    total_value_base: float
    is_empty: bool
    requires_rebalance: bool
    layers: dict[str, LayerDriftReport] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class VaultDriftReport:
    """Consolidated Model Portfolio drift report across the vault."""

    base_currency: str
    currency_symbol: str
    symbol_position: str
    portfolios: dict[str, PortfolioDriftReport] = field(default_factory=dict)

    @property
    def warning_portfolio_count(self) -> int:
        return sum(1 for p in self.portfolios.values() if p.requires_rebalance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_currency": self.base_currency,
            "warning_portfolio_count": self.warning_portfolio_count,
            "portfolios": {k: asdict(v) for k, v in self.portfolios.items()},
        }


def _normalize_name(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _format_currency(amount: float, loc: LocalizationConfig, signed: bool = True) -> str:
    sign = ("+" if amount >= 0 else "-") if signed else ("-" if amount < 0 else "")
    formatted_num = f"{abs(amount):,.0f}"
    if loc.symbol_position == "prefix":
        return f"{sign}{loc.currency_symbol}{formatted_num}"
    return f"{sign}{formatted_num} {loc.currency_symbol}"


def _asset_value_base(asset: Asset) -> float:
    if getattr(asset, "value_base", None) is not None:
        return float(asset.value_base or 0.0)
    return float(asset.value_pln or 0.0)


def _aggregate_layer_buckets(assets: list[Asset], layer_name: str) -> dict[str, float]:
    buckets: dict[str, float] = {}
    if layer_name == "asset_classes":
        buckets = {
            "Equities": 0.0,
            "Bonds": 0.0,
            "Real Estate": 0.0,
            "Commodities": 0.0,
            "Cash": 0.0,
        }
        for a in assets:
            val = _asset_value_base(a)
            alloc = getattr(a, "asset_allocation", None)
            if isinstance(alloc, str):
                try:
                    alloc = json.loads(alloc)
                except Exception:
                    alloc = None
            if isinstance(alloc, dict) and alloc:
                eq = float(alloc.get("equity") or alloc.get("equities") or 0.0) / 100.0
                bd = (
                    float(
                        alloc.get("bonds")
                        or alloc.get("bond")
                        or alloc.get("fixed_income")
                        or alloc.get("obligations")
                        or 0.0
                    )
                    / 100.0
                )
                re_w = float(alloc.get("real_estate") or alloc.get("reits") or 0.0) / 100.0
                cm = float(alloc.get("commodities") or alloc.get("commodity") or alloc.get("gold") or 0.0) / 100.0
                cs = float(alloc.get("cash") or 0.0) / 100.0
                if (eq + bd + re_w + cm + cs) > 0:
                    buckets["Equities"] += val * eq
                    buckets["Bonds"] += val * bd
                    buckets["Real Estate"] += val * re_w
                    buckets["Commodities"] += val * cm
                    buckets["Cash"] += val * cs
                else:
                    buckets["Equities"] += val
            else:
                atype = str(a.asset_type or "").lower()
                sec = str(a.dominant_sector or a.industry or "").lower()
                name = str(a.name or "").lower()
                ticker = str(a.ticker or "").lower()

                if atype == "cash" or "cash" in ticker or sec == "cash":
                    buckets["Cash"] += val
                elif "real estate" in atype or "real estate" in sec or "reit" in atype:
                    buckets["Real Estate"] += val
                elif "gold" in atype or "precious metals" in sec or "commodity" in atype or ticker == "gold":
                    buckets["Commodities"] += val
                elif sec == "sovereign" or "bond" in name or "treasury" in name or "bond" in atype:
                    buckets["Bonds"] += val
                else:
                    buckets["Equities"] += val
    elif layer_name == "sectors":
        for a in assets:
            val = _asset_value_base(a)
            sec_name = str(a.dominant_sector or a.industry or "Diversified").strip()
            buckets[sec_name] = buckets.get(sec_name, 0.0) + val
    elif layer_name == "assets":
        for a in assets:
            val = _asset_value_base(a)
            key = str(a.ticker or a.name or "").strip()
            if key:
                buckets[key] = buckets.get(key, 0.0) + val
    return buckets


def _lookup_bucket_value(buckets: dict[str, float], target_name: str) -> float:
    t_norm = _normalize_name(target_name)
    for b_key, b_val in buckets.items():
        b_norm = _normalize_name(b_key)
        if b_norm == t_norm:
            return b_val
        if ("bond" in t_norm or "obligation" in t_norm) and ("bond" in b_norm or "obligation" in b_norm):
            return b_val
        if ("gold" in t_norm or "commodit" in t_norm) and ("gold" in b_norm or "commodit" in b_norm):
            return b_val
    return buckets.get(target_name, 0.0)


def _evaluate_target_item(
    item: ModelPortfolioTargetItem,
    portfolio_cfg: ModelPortfolioConfig,
    actual_val: float,
    total_portfolio_value: float,
) -> TargetDriftResult:
    target_w = float(item.weight_pct)
    band = float(portfolio_cfg.get_tolerance_band(item))
    min_trade = float(portfolio_cfg.get_min_trade_amount(item))

    actual_w = (actual_val / total_portfolio_value) * 100.0 if total_portfolio_value > 0 else 0.0
    lower_bound = max(0.0, target_w - band)
    upper_bound = min(100.0, target_w + band)

    drift_pct = actual_w - target_w
    delta_base = ((target_w - actual_w) / 100.0) * total_portfolio_value

    corridor_breach_pct = 0.0
    is_over = actual_w > upper_bound + 1e-9
    is_under = actual_w < lower_bound - 1e-9

    if is_over:
        corridor_breach_pct = actual_w - upper_bound
    elif is_under:
        corridor_breach_pct = actual_w - lower_bound

    if not (is_over or is_under):
        status = TargetDriftStatus.BALANCED
        actionable = False
    elif abs(delta_base) < min_trade - 1e-9:
        status = TargetDriftStatus.BELOW_MIN_TRADE
        actionable = False
    else:
        status = TargetDriftStatus.OVERWEIGHT if is_over else TargetDriftStatus.UNDERWEIGHT
        actionable = True

    return TargetDriftResult(
        target=item.target,
        actual_value_base=actual_val,
        actual_weight_pct=actual_w,
        target_weight_pct=target_w,
        tolerance_band_pct=band,
        lower_bound_pct=lower_bound,
        upper_bound_pct=upper_bound,
        drift_pct=drift_pct,
        corridor_breach_pct=corridor_breach_pct,
        delta_base=delta_base,
        min_trade_amount=min_trade,
        is_actionable_breach=actionable,
        status=status,
    )


def evaluate_vault_model_portfolios(
    vault_path: str | None = None,
    portfolio_filter: str | None = None,
) -> VaultDriftReport:
    """Evaluate all configured Model Portfolios against live vault assets."""
    root_dir = os.path.abspath(vault_path or VAULT_ROOT)
    cfg: VaultConfig = load_vault_config(base_dir=root_dir, force_refresh=True)
    loc = cfg.localization

    assets_dir = os.path.join(root_dir, "10_Finance", "Assets")
    loaded_assets: list[Asset] = []
    if os.path.exists(assets_dir):
        for p in sorted(glob.glob(os.path.join(assets_dir, "*.md"))):
            try:
                loaded_assets.append(Asset.from_file(p))
            except Exception:
                continue

    report = VaultDriftReport(
        base_currency=loc.base_currency,
        currency_symbol=loc.currency_symbol,
        symbol_position=loc.symbol_position,
    )

    filter_norm = _normalize_name(portfolio_filter) if portfolio_filter else None

    for pkey, pcfg in cfg.model_portfolios.items():
        if filter_norm and filter_norm not in (_normalize_name(pkey), _normalize_name(pcfg.name)):
            continue

        target_norm = _normalize_name(pcfg.name)
        key_norm = _normalize_name(pkey)
        portfolio_assets = [
            a
            for a in loaded_assets
            if _normalize_name(a.portfolio) in (target_norm, key_norm)
            and (_asset_value_base(a) > 0 or a.name or a.ticker)
        ]
        total_val = sum(_asset_value_base(a) for a in portfolio_assets)
        is_empty = total_val <= 0.0

        p_report = PortfolioDriftReport(
            portfolio_key=pkey,
            portfolio_name=pcfg.name,
            rebalance_strategy=pcfg.rebalance_strategy,
            primary_layer=pcfg.primary_layer,
            total_value_base=total_val,
            is_empty=is_empty,
            requires_rebalance=False,
        )

        if not is_empty:
            for layer_name in ("asset_classes", "sectors", "assets"):
                layer_items: list[ModelPortfolioTargetItem] = getattr(pcfg.layers, layer_name, [])
                if not layer_items:
                    continue

                buckets = _aggregate_layer_buckets(portfolio_assets, layer_name)
                layer_rep = LayerDriftReport(
                    layer_name=layer_name,
                    is_primary=(layer_name == pcfg.primary_layer),
                )

                for item in layer_items:
                    actual_val = _lookup_bucket_value(buckets, item.target)
                    t_res = _evaluate_target_item(item, pcfg, actual_val, total_val)
                    layer_rep.targets.append(t_res)

                    if t_res.is_actionable_breach:
                        p_report.requires_rebalance = True
                        direction_label = (
                            "Overweight" if t_res.status == TargetDriftStatus.OVERWEIGHT else "Underweight"
                        )
                        breach_dir = "above" if t_res.corridor_breach_pct > 0 else "below"
                        drift_str = f"{t_res.drift_pct:+.1f}%"
                        breach_str = f"{t_res.corridor_breach_pct:+.1f}%"
                        delta_str = _format_currency(t_res.delta_base, loc, signed=True)
                        warn_msg = (
                            f"[WARN] {pcfg.name} ({layer_name}) — Rebalancing required: "
                            f"{t_res.target} is {direction_label} at {t_res.actual_weight_pct:.1f}% "
                            f"(target: {t_res.target_weight_pct:.1f}% ±{t_res.tolerance_band_pct:.1f}% "
                            f"[{t_res.lower_bound_pct:.1f}%–{t_res.upper_bound_pct:.1f}%], "
                            f"drift: {drift_str} from target / {breach_str} {breach_dir} corridor, "
                            f"delta: {delta_str})"
                        )
                        p_report.warnings.append(warn_msg)

                p_report.layers[layer_name] = layer_rep

        report.portfolios[pkey] = p_report

    return report


def run_check_model_portfolios(
    vault_path: str | None = None,
    portfolio_filter: str | None = None,
    strict: bool = False,
    as_json: bool = False,
) -> tuple[VaultDriftReport, int]:
    """Run Model Portfolio drift check, print CLI report, and return (report, exit_code)."""
    report = evaluate_vault_model_portfolios(vault_path=vault_path, portfolio_filter=portfolio_filter)

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("==================================================")
        print("⚖️  Running Model Portfolio Drift Check")
        print("==================================================")
        for p_rep in report.portfolios.values():
            if p_rep.is_empty:
                print(f"ℹ️  [EMPTY] {p_rep.portfolio_name}: No holdings (0 {report.base_currency}) — skipped.")
            elif p_rep.requires_rebalance:
                print(
                    f"⚠️  [WARN] {p_rep.portfolio_name}: Rebalancing required "
                    f"(strategy: {p_rep.rebalance_strategy}, value: {p_rep.total_value_base:,.2f} {report.base_currency})"
                )
                for w in p_rep.warnings:
                    print(f"   • {w}")
            else:
                print(
                    f"✅ [OK] {p_rep.portfolio_name}: All configured targets within Tolerance Corridor "
                    f"({p_rep.total_value_base:,.2f} {report.base_currency})."
                )
        print("==================================================")

    exit_code = 1 if (strict and report.warning_portfolio_count > 0) else 0
    return report, exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model Portfolio Drift Checker: evaluate portfolio buckets against Tolerance Corridors."
    )
    parser.add_argument(
        "--target",
        "--base-dir",
        dest="vault_path",
        default=None,
        help="Target vault root directory (default: current vault).",
    )
    parser.add_argument(
        "-p",
        "--portfolio",
        dest="portfolio",
        default=None,
        help="Check only a specific portfolio bucket (e.g. 'safety_net', 'long_term', 'aggressive').",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit code (1) if any portfolio requires rebalancing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report to stdout.",
    )
    args = parser.parse_args()

    _, exit_code = run_check_model_portfolios(
        vault_path=args.vault_path,
        portfolio_filter=args.portfolio,
        strict=args.strict,
        as_json=args.json,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
