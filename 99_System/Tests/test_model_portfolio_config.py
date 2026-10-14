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
    assert safety.min_trade_amount_pln == 500.0
    assert safety.primary_layer == "asset_classes"
    assert len(safety.layers.asset_classes) == 2
    assert safety.layers.asset_classes[0].target == "Bonds"
    assert safety.layers.asset_classes[0].weight_pct == 80.0
    assert safety.layers.asset_classes[1].target == "Cash"
    assert safety.layers.asset_classes[1].weight_pct == 20.0

    # Long Term
    long_term = cfg.model_portfolios["long_term"]
    assert long_term.name == "Long term"
    assert long_term.min_trade_amount_pln == 1000.0
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


def test_layer_validation_sum_to_100() -> None:
    """Verify layer validation enforces sum of weight_pct equals 100.0%."""
    # Valid sum
    valid_layers = ModelPortfolioLayers(
        asset_classes=[
            ModelPortfolioTargetItem(target="Equities", weight_pct=60.0),
            ModelPortfolioTargetItem(target="Bonds", weight_pct=40.0),
        ]
    )
    assert len(valid_layers.asset_classes) == 2

    # Under-allocation (sum < 100%)
    with pytest.raises(ValidationError, match="asset_classes.*must sum to 100.0%"):
        ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=60.0),
                ModelPortfolioTargetItem(target="Bonds", weight_pct=30.0),
            ]
        )

    # Over-allocation (sum > 100%)
    with pytest.raises(ValidationError, match="sectors.*must sum to 100.0%"):
        ModelPortfolioLayers(
            sectors=[
                ModelPortfolioTargetItem(target="Technology", weight_pct=70.0),
                ModelPortfolioTargetItem(target="Healthcare", weight_pct=40.0),
            ]
        )


def test_target_item_overrides_and_defaults() -> None:
    """Verify portfolio defaults and per-target overrides for corridors and thresholds."""
    portfolio = ModelPortfolioConfig(
        name="Test Portfolio",
        tolerance_band_pct=5.0,
        min_trade_amount_pln=500.0,
        layers=ModelPortfolioLayers(
            asset_classes=[
                ModelPortfolioTargetItem(target="Equities", weight_pct=80.0),
                ModelPortfolioTargetItem(
                    target="Cash",
                    weight_pct=20.0,
                    tolerance_band_pct=2.0,
                    min_trade_amount_pln=100.0,
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
