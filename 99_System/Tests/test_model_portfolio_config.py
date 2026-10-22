"""Unit tests for Model Portfolio configuration and validation (config.yaml)."""

import pytest
from model.config import (
    ModelPortfolioConfig,
    ModelPortfolioLayers,
    ModelPortfolioTargetItem,
    load_vault_config,
)
from pydantic import ValidationError


def test_load_model_portfolios_from_config_yaml() -> None:
    """Verify default model portfolios defined in config.yaml parse correctly."""
    cfg = load_vault_config(force_refresh=True)
    assert "safety_net" in cfg.model_portfolios
    assert "long_term" in cfg.model_portfolios
    assert "aggressive" in cfg.model_portfolios

    # Safety Net
    safety = cfg.model_portfolios["safety_net"]
    assert safety.name == "Safety net"
    assert safety.rebalance_strategy == "inflow_first"
    assert safety.tolerance_band_pct == 5.0
    assert safety.min_trade_amount == 500.0
    assert safety.primary_layer == "asset_classes"
    assert len(safety.layers.asset_classes) == 2
    assert safety.layers.asset_classes[0].target == "Bonds"
    assert safety.layers.asset_classes[0].weight_pct == 80.0
    assert safety.layers.asset_classes[1].target == "Cash"
    assert safety.layers.asset_classes[1].weight_pct == 20.0

    # Long Term
    long_term = cfg.model_portfolios["long_term"]
    assert long_term.name == "Long term"
    assert long_term.min_trade_amount == 1000.0
    assert len(long_term.layers.asset_classes) == 2
    assert long_term.layers.asset_classes[0].target == "Equities"
    assert long_term.layers.asset_classes[0].weight_pct == 80.0
    assert long_term.layers.asset_classes[1].target == "Bonds"
    assert long_term.layers.asset_classes[1].weight_pct == 20.0

    # Aggressive
    agg = cfg.model_portfolios["aggressive"]
    assert agg.name == "Aggressive"
    assert len(agg.layers.asset_classes) == 2
    assert agg.layers.asset_classes[0].target == "Equities"
    assert agg.layers.asset_classes[0].weight_pct == 90.0
    assert agg.layers.asset_classes[1].target == "Cash"
    assert agg.layers.asset_classes[1].weight_pct == 10.0


def test_get_model_portfolio_resolution() -> None:
    """Verify get_model_portfolio matches case-insensitive, underscored, or spaced names."""
    cfg = load_vault_config(force_refresh=True)

    # Safety Net resolution
    assert cfg.get_model_portfolio("Safety net") is not None
    assert cfg.get_model_portfolio("safety net") is not None
    assert cfg.get_model_portfolio("safety_net") is not None
    assert cfg.get_model_portfolio("Safety Net") is not None
    assert cfg.get_model_portfolio("safety-net") is not None
    assert cfg.get_model_portfolio("safetynet") is not None

    # Long Term resolution
    assert cfg.get_model_portfolio("Long term") is not None
    assert cfg.get_model_portfolio("long_term") is not None

    # Aggressive resolution
    assert cfg.get_model_portfolio("Aggressive") is not None
    assert cfg.get_model_portfolio("aggressive") is not None

    # Unknown / empty returns None
    assert cfg.get_model_portfolio("Nonexistent") is None
    assert cfg.get_model_portfolio("") is None
    assert cfg.get_model_portfolio(None) is None


def test_layer_validation_partial_and_max_100() -> None:
    """Verify layer validation allows partial sums (0 < sum <= 100.0%) and rejects > 100%, <= 0%, or duplicates."""
    # 1. Valid full 100% sum
    valid_full = ModelPortfolioLayers(
        asset_classes=[
            ModelPortfolioTargetItem(target="Equities", weight_pct=60.0),
            ModelPortfolioTargetItem(target="Bonds", weight_pct=40.0),
        ]
    )
    assert len(valid_full.asset_classes) == 2

    # 2. Valid partial allocation (sum < 100%, e.g. 30% Equities + 30% Bonds = 60%)
    valid_partial = ModelPortfolioLayers(
        asset_classes=[
            ModelPortfolioTargetItem(target="Equities", weight_pct=30.0),
            ModelPortfolioTargetItem(target="Bonds", weight_pct=30.0),
        ]
    )
    assert sum(item.weight_pct for item in valid_partial.asset_classes) == 60.0

    # 3. Over-allocation (sum > 100%)
    with pytest.raises(ValidationError, match="sectors.*cannot exceed 100.0%"):
        ModelPortfolioLayers(
            sectors=[
                ModelPortfolioTargetItem(target="Technology", weight_pct=70.0),
                ModelPortfolioTargetItem(target="Healthcare", weight_pct=40.0),
            ]
        )

    # 4. Zero total allocation (sum <= 0%)
    with pytest.raises(ValidationError, match="asset_classes.*must be greater than 0%"):
        ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=0.0),
            ]
        )

    # 5. Duplicate target in the same layer
    with pytest.raises(ValidationError, match="Duplicate target"):
        ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=30.0),
                ModelPortfolioTargetItem(target="equities", weight_pct=20.0),
            ]
        )


def test_target_item_overrides_and_defaults() -> None:
    """Verify portfolio defaults and per-target overrides for corridors and thresholds."""
    portfolio = ModelPortfolioConfig(
        name="Test Portfolio",
        tolerance_band_pct=5.0,
        min_trade_amount=500.0,
        layers=ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=80.0),
                ModelPortfolioTargetItem(
                    target="Cash",
                    weight_pct=20.0,
                    tolerance_band_pct=2.0,
                    min_trade_amount=100.0,
                ),
            ]
        ),
    )

    eq_item = portfolio.layers.asset_classes[0]
    cash_item = portfolio.layers.asset_classes[1]

    # Equities uses portfolio defaults
    assert portfolio.get_tolerance_band(eq_item) == 5.0
    assert portfolio.get_min_trade_amount(eq_item) == 500.0

    # Cash uses custom item-level overrides
    assert portfolio.get_tolerance_band(cash_item) == 2.0
    assert portfolio.get_min_trade_amount(cash_item) == 100.0


def test_multi_layer_portfolio() -> None:
    """Verify a portfolio can define multiple independent layers."""
    portfolio = ModelPortfolioConfig(
        name="Multi Layer",
        primary_layer="asset_classes",
        layers=ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=70.0),
                ModelPortfolioTargetItem(target="Bonds", weight_pct=30.0),
            ],
            sectors=[
                ModelPortfolioTargetItem(target="Technology", weight_pct=50.0),
                ModelPortfolioTargetItem(target="Military", weight_pct=30.0),
                ModelPortfolioTargetItem(target="Healthcare", weight_pct=20.0),
            ],
            assets=[
                ModelPortfolioTargetItem(target="VWCE", weight_pct=50.0),
                ModelPortfolioTargetItem(target="V80A", weight_pct=30.0),
                ModelPortfolioTargetItem(target="EDO0936", weight_pct=20.0),
            ],
        ),
    )
    assert len(portfolio.layers.asset_classes) == 2
    assert len(portfolio.layers.sectors) == 3
    assert len(portfolio.layers.assets) == 3


def test_default_taxonomies_and_overrides() -> None:
    """Verify built-in default taxonomies (sectors and issuers) load and support custom overrides."""
    cfg = load_vault_config(force_refresh=True)

    # 1. Defaults loaded even when not explicitly in config.yaml
    assert "ishares" in cfg.etf.issuer.discovery_mapping
    assert cfg.etf.issuer.discovery_mapping["vanguard"] == "Vanguard"
    assert "Healthcare" in cfg.dominant_sector.thresholds
    assert cfg.dominant_sector.thresholds["Healthcare"] == 80.0
    assert "financial_services" in cfg.dominant_sector.mappings
    assert cfg.dominant_sector.mappings["financial_services"] == "Finance"

    # 2. Custom overrides merge cleanly with defaults
    from model.config import DominantSectorConfig, EtfIssuerConfig

    custom_issuer = EtfIssuerConfig.model_validate({"discovery_mapping": {"custom_fund": "Custom Fund"}})
    assert custom_issuer.discovery_mapping["custom_fund"] == "Custom Fund"
    assert custom_issuer.discovery_mapping["ishares"] == "iShares"

    custom_sector = DominantSectorConfig.model_validate(
        {
            "thresholds": {"CustomSector": 65.0},
            "mappings": {"custom_sub": "CustomSector"},
        }
    )
    assert custom_sector.thresholds["CustomSector"] == 65.0
    assert custom_sector.thresholds["Healthcare"] == 80.0
    assert custom_sector.mappings["custom_sub"] == "CustomSector"
    assert custom_sector.mappings["financial_services"] == "Finance"


def test_user_profile_config_loading_and_defaults() -> None:
    """Verify user_profile section loads properly from config.yaml and applies valid defaults."""
    cfg = load_vault_config(force_refresh=True)
    assert cfg.user_profile is not None
    assert cfg.user_profile.risk_tolerance in ("conservative", "moderate", "aggressive")
    assert cfg.user_profile.max_single_stock_pct == 15.0
    assert cfg.user_profile.tax_sensitive is True
    assert cfg.user_profile.allow_profit_harvesting is True
    assert "mbank_ike" in cfg.user_profile.tax_advantaged_priority


def test_user_profile_validation() -> None:
    """Verify UserProfileConfig enforces valid range and literal constraints."""
    from model.config import UserProfileConfig

    # Valid custom configuration
    custom = UserProfileConfig(
        risk_tolerance="conservative",
        max_single_stock_pct=10.0,
        tax_sensitive=False,
        allow_profit_harvesting=False,
    )
    assert custom.risk_tolerance == "conservative"
    assert custom.max_single_stock_pct == 10.0
    assert custom.tax_sensitive is False

    # Invalid risk_tolerance
    with pytest.raises(ValidationError):
        UserProfileConfig(risk_tolerance="reckless")  # type: ignore[arg-type]

    # Invalid max_single_stock_pct (> 100 or < 1)
    with pytest.raises(ValidationError):
        UserProfileConfig(max_single_stock_pct=150.0)

    with pytest.raises(ValidationError):
        UserProfileConfig(max_single_stock_pct=0.5)


def test_init_vault_update_user_profile(tmp_path: pytest.TempPathFactory) -> None:
    """Verify _update_user_profile_in_config updates or appends user_profile in config.yaml."""
    from init_vault import _update_user_profile_in_config

    cfg_file = tmp_path / "config.yaml"  # type: ignore[operator]
    cfg_file.write_text("model_portfolios: {}\n", encoding="utf-8")

    # 1. Append when missing
    _update_user_profile_in_config(
        str(cfg_file),
        risk_tolerance="aggressive",
        tax_sensitive=False,
        max_single_stock_pct=20.0,
        allow_profit_harvesting=True,
    )
    content = cfg_file.read_text(encoding="utf-8")
    assert 'risk_tolerance: "aggressive"' in content
    assert "max_single_stock_pct: 20.0" in content
    assert "tax_sensitive: false" in content
    assert "allow_profit_harvesting: true" in content

    # 2. Update existing in-place
    _update_user_profile_in_config(
        str(cfg_file),
        risk_tolerance="conservative",
        tax_sensitive=True,
        max_single_stock_pct=12.5,
        allow_profit_harvesting=False,
    )
    content2 = cfg_file.read_text(encoding="utf-8")
    assert 'risk_tolerance: "conservative"' in content2
    assert "max_single_stock_pct: 12.5" in content2
    assert "tax_sensitive: true" in content2
    assert "allow_profit_harvesting: false" in content2


def test_localization_config() -> None:
    """Verify localization configuration loads with expected defaults and symbols."""
    cfg = load_vault_config(force_refresh=True)
    assert cfg.localization is not None
    assert cfg.localization.base_currency == "PLN"
    assert cfg.localization.currency_symbol == "zł"
    assert cfg.localization.symbol_position == "suffix"
    assert "PLN" in cfg.localization.supported_currencies
    assert "EUR" in cfg.localization.supported_currencies
    assert "USD" in cfg.localization.supported_currencies


def test_interactive_setup_model_portfolios_custom_layers_and_tolerances(tmp_path: pytest.TempPathFactory) -> None:
    """Seam 1: Interactive wizard customizes portfolio corridors, per-target tolerance overrides, and partial layers."""
    from unittest.mock import patch

    from setup_model_portfolios import run_setup_model_portfolios

    cfg_file = tmp_path / "config.yaml"  # type: ignore[operator]
    cfg_file.write_text(
        "# Header comment preserved\n"
        "localization:\n"
        '  base_currency: "PLN"\n'
        "\n"
        "user_profile:\n"
        '  risk_tolerance: "moderate"\n'
        "  max_single_stock_pct: 15.0\n",
        encoding="utf-8",
    )

    # Simulated interactive session:
    # 1. Preset choice: "1" (Balanced starter)
    # 2. Single-stock cap: "12" (12.0%)
    # 3. Customize portfolios?: "y"
    # 4. Main menu: "1" (Safety net)
    #    - Display name: "" (keep "Safety net")
    #    - Strategy: "2" (full_rebalance)
    #    - Tolerance band: "4.0"
    #    - Min trade amount: "250"
    #    - Primary layer: "1" (asset_classes)
    #    - Layer action: "C" -> confirm "y" (clear preset items)
    #    - Layer action: "A" -> target "Equities", weight "30", tol override "", min trade override ""
    #    - Layer action: "A" -> target "Bonds", weight "30", tol override "2.5", min trade override "100"
    #    - Layer action: "F" -> allocate remainder to Cash? "n" (keep partial 60% sum!)
    # 5. Main menu: "3" (Aggressive)
    #    - Display name: "" (keep "Aggressive")
    #    - Strategy: "" (keep inflow_first)
    #    - Tolerance band: "" (keep 5.0)
    #    - Min trade amount: "" (keep 500.0)
    #    - Primary layer: "3" (sectors)
    #    - Layer action: "A" -> target "Technology", weight "60", tol override "3.0", min trade override ""
    #    - Layer action: "A" -> target "Military", weight "40", tol override "", min trade override ""
    #    - Layer action: "F" (sum is 100%, finishes immediately)
    # 6. Main menu: "S" (Save changes to config.yaml and Exit)
    user_inputs = [
        "1",
        "12",
        "y",
        "1",
        "",
        "2",
        "4.0",
        "250",
        "1",
        "C",
        "y",
        "A",
        "Equities",
        "30",
        "",
        "",
        "A",
        "Bonds",
        "30",
        "2.5",
        "100",
        "F",
        "n",
        "3",
        "",
        "",
        "",
        "",
        "3",
        "A",
        "Technology",
        "60",
        "3.0",
        "",
        "A",
        "Military",
        "40",
        "",
        "",
        "F",
        "S",
    ]

    with patch("builtins.input", side_effect=user_inputs):
        ok = run_setup_model_portfolios(target_dir=str(tmp_path), interactive=True)
        assert ok is True

    raw_text = cfg_file.read_text(encoding="utf-8")
    assert "# Header comment preserved" in raw_text
    assert "min_trade_amount:" in raw_text
    assert "min_trade_amount_pln:" not in raw_text

    loaded = load_vault_config(base_dir=str(tmp_path), force_refresh=True)
    assert loaded.user_profile.max_single_stock_pct == 12.0

    safety = loaded.model_portfolios["safety_net"]
    assert safety.rebalance_strategy == "full_rebalance"
    assert safety.tolerance_band_pct == 4.0
    assert safety.min_trade_amount == 250.0
    assert safety.primary_layer == "asset_classes"
    assert len(safety.layers.asset_classes) == 2
    assert safety.layers.asset_classes[0].target == "Equities"
    assert safety.layers.asset_classes[0].weight_pct == 30.0
    assert safety.layers.asset_classes[0].tolerance_band_pct is None
    assert safety.get_tolerance_band(safety.layers.asset_classes[0]) == 4.0
    assert safety.layers.asset_classes[1].target == "Bonds"
    assert safety.layers.asset_classes[1].weight_pct == 30.0
    assert safety.layers.asset_classes[1].tolerance_band_pct == 2.5
    assert safety.layers.asset_classes[1].min_trade_amount == 100.0
    assert safety.get_tolerance_band(safety.layers.asset_classes[1]) == 2.5
    assert safety.get_min_trade_amount(safety.layers.asset_classes[1]) == 100.0

    agg = loaded.model_portfolios["aggressive"]
    assert agg.primary_layer == "sectors"
    assert len(agg.layers.sectors) == 2
    assert agg.layers.sectors[0].target == "Technology"
    assert agg.layers.sectors[0].weight_pct == 60.0
    assert agg.layers.sectors[0].tolerance_band_pct == 3.0
    assert agg.layers.sectors[1].target == "Military"
    assert agg.layers.sectors[1].weight_pct == 40.0
    assert agg.layers.sectors[1].tolerance_band_pct is None


def test_run_py_setup_model_portfolios_flag(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Seam 1: run.py --setup-model-portfolios launches interactive model portfolio configurator."""
    import sys
    from unittest.mock import patch

    import run as runner_mod

    cfg_file = tmp_path / "config.yaml"  # type: ignore[operator]
    cfg_file.write_text("localization:\n  base_currency: PLN\n", encoding="utf-8")

    # Immediately save default presets ("S") in interactive_main
    monkeypatch.setattr(
        sys,
        "argv",
        ["run.py", "--setup-model-portfolios", "--base-dir", str(tmp_path)],
    )
    with patch("builtins.input", side_effect=["S"]):
        exit_code = runner_mod.main()
        assert exit_code == 0

    loaded = load_vault_config(base_dir=str(tmp_path), force_refresh=True)
    assert "safety_net" in loaded.model_portfolios
    assert "long_term" in loaded.model_portfolios
    assert "aggressive" in loaded.model_portfolios
