"""Unit tests for Model Portfolio Drift Evaluation Engine (check_model_portfolios.py)."""

import os
import sys

import pytest

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _write_asset_note(
    assets_dir: str,
    filename: str,
    *,
    name: str,
    ticker: str,
    portfolio: str,
    asset_type: str,
    value_base: float,
    dominant_sector: str = "Diversified",
    asset_allocation: str | None = None,
) -> None:
    os.makedirs(assets_dir, exist_ok=True)
    alloc_line = f"asset_allocation: '{asset_allocation}'\n" if asset_allocation else ""
    content = (
        "---\n"
        f'name: "{name}"\n'
        f'ticker: "{ticker}"\n'
        f'portfolio: "{portfolio}"\n'
        f'asset_type: "{asset_type}"\n'
        f'dominant_sector: "{dominant_sector}"\n'
        f"value_base: {value_base}\n"
        f"value_pln: {value_base}\n"
        f"{alloc_line}"
        "---\n"
        f"# {name}\n"
    )
    with open(os.path.join(assets_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)


def test_detects_overweight_and_underweight_corridor_breach(
    tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    """Seam 2 (Slice 4): Detects corridor breach and reports both drift from target and corridor breach amount."""
    from check_model_portfolios import TargetDriftStatus, run_check_model_portfolios

    vault_dir = str(tmp_path)
    config_path = os.path.join(vault_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(
            "localization:\n"
            '  base_currency: "PLN"\n'
            '  currency_symbol: "zł"\n'
            '  symbol_position: "suffix"\n'
            "model_portfolios:\n"
            "  safety_net:\n"
            '    name: "Safety net"\n'
            '    rebalance_strategy: "inflow_first"\n'
            "    tolerance_band_pct: 5.0\n"
            "    min_trade_amount: 500.0\n"
            '    primary_layer: "asset_classes"\n'
            "    layers:\n"
            "      asset_classes:\n"
            '        - target: "Bonds"\n'
            "          weight_pct: 80.0\n"
            '        - target: "Cash"\n'
            "          weight_pct: 20.0\n"
        )

    assets_dir = os.path.join(vault_dir, "10_Finance", "Assets")
    _write_asset_note(
        assets_dir,
        "EDO0936.md",
        name="Treasury Bonds EDO0936",
        ticker="EDO0936",
        portfolio="Safety net",
        asset_type="bond",
        dominant_sector="Sovereign",
        value_base=88500.0,
    )
    _write_asset_note(
        assets_dir,
        "Cash_PLN.md",
        name="Bank Cash Reserve",
        ticker="CASH_PLN",
        portfolio="Safety net",
        asset_type="cash",
        dominant_sector="Cash",
        value_base=11500.0,
    )

    report, exit_code = run_check_model_portfolios(vault_path=vault_dir)
    assert exit_code == 0
    assert report.warning_portfolio_count == 1

    safety_report = report.portfolios["safety_net"]
    assert safety_report.requires_rebalance is True
    assert safety_report.total_value_base == pytest.approx(100000.0)

    layer_report = safety_report.layers["asset_classes"]
    bonds_res = next(t for t in layer_report.targets if t.target == "Bonds")
    assert bonds_res.status == TargetDriftStatus.OVERWEIGHT
    assert bonds_res.actual_weight_pct == pytest.approx(88.5)
    assert bonds_res.lower_bound_pct == pytest.approx(75.0)
    assert bonds_res.upper_bound_pct == pytest.approx(85.0)
    assert bonds_res.drift_pct == pytest.approx(8.5)
    assert bonds_res.corridor_breach_pct == pytest.approx(3.5)
    assert bonds_res.delta_base == pytest.approx(-8500.0)
    assert bonds_res.is_actionable_breach is True

    cash_res = next(t for t in layer_report.targets if t.target == "Cash")
    assert cash_res.status == TargetDriftStatus.UNDERWEIGHT
    assert cash_res.actual_weight_pct == pytest.approx(11.5)
    assert cash_res.drift_pct == pytest.approx(-8.5)
    assert cash_res.corridor_breach_pct == pytest.approx(-3.5)
    assert cash_res.delta_base == pytest.approx(8500.0)
    assert cash_res.is_actionable_breach is True

    captured = capsys.readouterr().out
    assert "WARN" in captured
    assert "Safety net" in captured
    assert "Bonds" in captured
    assert "88.5%" in captured
    assert "+8.5%" in captured
    assert "+3.5%" in captured


def test_partial_model_unmodeled_asset_empty_portfolio_and_below_min_trade(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Seam 2 (Slice 5 & 6): Partial layer (30% Eq, 30% Bd + 27% unmodeled Gold), empty bucket, and below min_trade."""
    from check_model_portfolios import TargetDriftStatus, run_check_model_portfolios

    vault_dir = str(tmp_path)
    config_path = os.path.join(vault_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(
            "localization:\n"
            '  base_currency: "PLN"\n'
            "model_portfolios:\n"
            "  safety_net:\n"
            '    name: "Safety net"\n'
            "    tolerance_band_pct: 5.0\n"
            "    min_trade_amount: 500.0\n"
            '    primary_layer: "asset_classes"\n'
            "    layers:\n"
            "      asset_classes:\n"
            '        - target: "Bonds"\n'
            "          weight_pct: 80.0\n"
            "  long_term:\n"
            '    name: "Long term"\n'
            "    tolerance_band_pct: 5.0\n"
            "    min_trade_amount: 500.0\n"
            '    primary_layer: "asset_classes"\n'
            "    layers:\n"
            "      asset_classes:\n"
            '        - target: "Equities"\n'
            "          weight_pct: 30.0\n"
            '        - target: "Bonds"\n'
            "          weight_pct: 30.0\n"
            "  aggressive:\n"
            '    name: "Aggressive"\n'
            "    tolerance_band_pct: 5.0\n"
            "    min_trade_amount: 500.0\n"
            '    primary_layer: "asset_classes"\n'
            "    layers:\n"
            "      asset_classes:\n"
            '        - target: "Equities"\n'
            "          weight_pct: 80.0\n"
            "          tolerance_band_pct: 3.0\n"
        )

    assets_dir = os.path.join(vault_dir, "10_Finance", "Assets")
    # 1. Safety net has NO assets -> empty portfolio (total_value == 0)

    # 2. Long term has 33% Equities (33,000), 40% Bonds (40,000), and 27% unmodeled Gold (27,000) = 100,000 total
    _write_asset_note(
        assets_dir,
        "VWCE.md",
        name="Vanguard FTSE All-World",
        ticker="VWCE",
        portfolio="Long term",
        asset_type="etf",
        value_base=33000.0,
    )
    _write_asset_note(
        assets_dir,
        "EDO.md",
        name="Treasury Bonds EDO",
        ticker="EDO",
        portfolio="Long term",
        asset_type="bond",
        dominant_sector="Sovereign",
        value_base=40000.0,
    )
    _write_asset_note(
        assets_dir,
        "Gold.md",
        name="Physical Gold",
        ticker="GOLD",
        portfolio="Long term",
        asset_type="gold",
        dominant_sector="Precious Metals",
        value_base=27000.0,
    )

    # 3. Aggressive has 5,000 total: 4,300 Equities (86% vs 80% ±3% [77%-83%]) and 700 Cash (14%).
    # Delta is -300 PLN, which is < min_trade_amount (500 PLN) -> ignored!
    _write_asset_note(
        assets_dir,
        "NVDA.md",
        name="NVIDIA",
        ticker="NVDA",
        portfolio="Aggressive",
        asset_type="stock",
        dominant_sector="Technology",
        value_base=4300.0,
    )
    _write_asset_note(
        assets_dir,
        "Agg_Cash.md",
        name="Broker Cash",
        ticker="CASH",
        portfolio="Aggressive",
        asset_type="cash",
        dominant_sector="Cash",
        value_base=700.0,
    )

    report, exit_code = run_check_model_portfolios(vault_path=vault_dir)
    assert exit_code == 0

    # Safety net: empty -> ignored
    safety_rep = report.portfolios["safety_net"]
    assert safety_rep.is_empty is True
    assert safety_rep.requires_rebalance is False
    assert len(safety_rep.warnings) == 0

    # Long term: Gold (27%) is included in 100k denominator, Equities (33%) is BALANCED, ONLY Bonds (40%) triggers WARN
    lt_rep = report.portfolios["long_term"]
    assert lt_rep.total_value_base == pytest.approx(100000.0)
    assert lt_rep.requires_rebalance is True
    assert len(lt_rep.warnings) == 1
    assert "Bonds" in lt_rep.warnings[0]
    assert "Gold" not in lt_rep.warnings[0]
    assert "Equities" not in lt_rep.warnings[0]

    lt_targets = {t.target: t for t in lt_rep.layers["asset_classes"].targets}
    assert set(lt_targets.keys()) == {"Equities", "Bonds"}
    assert lt_targets["Equities"].actual_weight_pct == pytest.approx(33.0)
    assert lt_targets["Equities"].status == TargetDriftStatus.BALANCED
    assert lt_targets["Equities"].is_actionable_breach is False

    assert lt_targets["Bonds"].actual_weight_pct == pytest.approx(40.0)
    assert lt_targets["Bonds"].drift_pct == pytest.approx(10.0)
    assert lt_targets["Bonds"].corridor_breach_pct == pytest.approx(5.0)
    assert lt_targets["Bonds"].delta_base == pytest.approx(-10000.0)
    assert lt_targets["Bonds"].status == TargetDriftStatus.OVERWEIGHT
    assert lt_targets["Bonds"].is_actionable_breach is True

    # Aggressive: Equities (86% vs [77%-83%]) has delta -300 PLN < 500 PLN min_trade_amount -> ignored!
    agg_rep = report.portfolios["aggressive"]
    assert agg_rep.requires_rebalance is False
    assert len(agg_rep.warnings) == 0
    agg_eq = agg_rep.layers["asset_classes"].targets[0]
    assert agg_eq.tolerance_band_pct == pytest.approx(3.0)
    assert agg_eq.actual_weight_pct == pytest.approx(86.0)
    assert agg_eq.corridor_breach_pct == pytest.approx(3.0)
    assert agg_eq.delta_base == pytest.approx(-300.0)
    assert agg_eq.status == TargetDriftStatus.BELOW_MIN_TRADE
    assert agg_eq.is_actionable_breach is False

    # Strict mode returns exit code 1 because long_term has 1 actionable warning
    _, strict_code = run_check_model_portfolios(vault_path=vault_dir, strict=True)
    assert strict_code == 1


def test_cli_main_and_run_py_rebalance_step(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Seam 2 (Slice 7): Standalone CLI main() and run.py --rebalance execute drift check across layers."""
    import check_model_portfolios

    import run as runner_mod

    vault_dir = str(tmp_path)
    config_path = os.path.join(vault_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(
            "localization:\n"
            '  base_currency: "EUR"\n'
            '  currency_symbol: "€"\n'
            '  symbol_position: "suffix"\n'
            "model_portfolios:\n"
            "  aggressive:\n"
            '    name: "Aggressive"\n'
            "    tolerance_band_pct: 5.0\n"
            "    min_trade_amount: 500.0\n"
            '    primary_layer: "sectors"\n'
            "    layers:\n"
            "      sectors:\n"
            '        - target: "Technology"\n'
            "          weight_pct: 50.0\n"
            "      assets:\n"
            '        - target: "NVDA"\n'
            "          weight_pct: 30.0\n"
            "          tolerance_band_pct: 4.0\n"
        )

    assets_dir = os.path.join(vault_dir, "10_Finance", "Assets")
    _write_asset_note(
        assets_dir,
        "NVDA.md",
        name="NVIDIA",
        ticker="NVDA",
        portfolio="Aggressive",
        asset_type="stock",
        dominant_sector="Technology",
        value_base=65000.0,
    )
    _write_asset_note(
        assets_dir,
        "RHM.md",
        name="Rheinmetall",
        ticker="RHM",
        portfolio="Aggressive",
        asset_type="stock",
        dominant_sector="Military",
        value_base=35000.0,
    )

    # 1. Standalone CLI main() with --strict returns 1 when breach is detected
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_model_portfolios.py", "--target", vault_dir, "--strict"],
    )
    assert check_model_portfolios.main() == 1

    # 2. Unified runner `python run.py --rebalance` executes step and returns 0
    monkeypatch.setattr(
        sys,
        "argv",
        ["run.py", "--rebalance", "--base-dir", vault_dir, "--no-progress"],
    )
    assert runner_mod.main() == 0
    out = capsys.readouterr().out
    assert "Technology" in out
    assert "NVDA" in out
