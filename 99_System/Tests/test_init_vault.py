"""Unit tests for vault initialization and localization configuration."""

import os
import sys
import tempfile
from unittest.mock import patch

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from init_vault import (
    VAULT_ROOT,
    _update_localization_in_config,
    configure_localization,
    init_vault,
    prompt_base_currency_selection,
    prompt_clean_mode,
    purge_sample_data,
    scaffold_target_vault,
)


def test_prompt_base_currency_empty_input_defaults_to_pln():
    supported = ["PLN", "EUR", "USD", "GBP", "CHF"]
    with patch("builtins.input", return_value=""):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "PLN"
        assert symbol == "zł"
        assert pos == "suffix"


def test_prompt_base_currency_exact_match():
    supported = ["PLN", "EUR", "USD", "GBP", "CHF"]
    with patch("builtins.input", return_value="USD"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "USD"
        assert symbol == "$"
        assert pos == "prefix"

    with patch("builtins.input", return_value="eur"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "EUR"
        assert symbol == "€"
        assert pos == "suffix"


def test_prompt_base_currency_prefix_autocomplete():
    supported = ["PLN", "EUR", "USD", "GBP", "CHF"]

    # "P" -> PLN
    with patch("builtins.input", return_value="P"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "PLN"
        assert symbol == "zł"
        assert pos == "suffix"

    # "u" -> USD
    with patch("builtins.input", return_value="u"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "USD"
        assert symbol == "$"
        assert pos == "prefix"

    # "g" -> GBP
    with patch("builtins.input", return_value="g"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "GBP"
        assert symbol == "£"
        assert pos == "prefix"


def test_prompt_base_currency_disambiguation():
    supported = ["CAD", "CHF", "EUR", "USD"]

    # "C" matches CAD (1) and CHF (2) -> choose 2
    with patch("builtins.input", side_effect=["C", "2"]):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "CHF"
        assert symbol == "CHF"
        assert pos == "suffix"

    # "C" matches CAD (1) and CHF (2) -> choose 1
    with patch("builtins.input", side_effect=["C", "1"]):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "CAD"
        assert symbol == "$"
        assert pos == "prefix"


def test_prompt_base_currency_custom_iso():
    supported = ["PLN", "EUR", "USD"]
    # 3-letter uppercase alphabetic code not in supported list
    with patch("builtins.input", return_value="SEK"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "SEK"
        assert symbol == "kr"
        assert pos == "suffix"

    # Unknown custom 3-letter code not in DEFAULT_CURRENCY_SYMBOLS
    with patch("builtins.input", return_value="XYZ"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "XYZ"
        assert symbol == "XYZ"
        assert pos == "suffix"


def test_prompt_base_currency_invalid_input_fallback():
    supported = ["PLN", "EUR", "USD"]
    with patch("builtins.input", return_value="INVALID_TOKEN"):
        curr, symbol, pos = prompt_base_currency_selection(supported)
        assert curr == "PLN"
        assert symbol == "zł"
        assert pos == "suffix"


def test_update_localization_in_config():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "config.yaml")

        # 1. Create initial config without localization
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("portfolio_currency: PLN\n")

        _update_localization_in_config(
            config_path,
            base_currency="EUR",
            currency_symbol="€",
            symbol_position="suffix",
            supported_currencies=["EUR", "USD", "PLN"],
        )

        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        assert "localization:" in content
        assert 'base_currency: "EUR"' in content
        assert 'currency_symbol: "€"' in content
        assert 'symbol_position: "suffix"' in content

        # 2. Update existing localization block in-place
        _update_localization_in_config(
            config_path,
            base_currency="USD",
            currency_symbol="$",
            symbol_position="prefix",
        )

        with open(config_path, encoding="utf-8") as f:
            updated_content = f.read()

        assert 'base_currency: "USD"' in updated_content
        assert 'currency_symbol: "$"' in updated_content
        assert 'symbol_position: "prefix"' in updated_content


def test_configure_localization_non_interactive():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# sample config\n")

        curr, symbol, pos = configure_localization(tmp_dir, interactive=False)
        assert curr == "PLN"
        assert symbol == "zł"
        assert pos == "suffix"

        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        assert 'base_currency: "PLN"' in content


def test_prompt_clean_mode():
    with patch("builtins.input", return_value=""):
        assert prompt_clean_mode() is True

    with patch("builtins.input", return_value="1"):
        assert prompt_clean_mode() is True

    with patch("builtins.input", return_value="2"):
        assert prompt_clean_mode() is False


def test_purge_sample_data():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Setup mock vault structure with sample files
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        etf_dir = os.path.join(tmp_dir, "10_Finance", "ETF_Holdings")
        raw_degiro = os.path.join(tmp_dir, "00_Raw", "degiro")
        decisions_2026 = os.path.join(tmp_dir, "20_Decisions", "2026")
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")

        os.makedirs(assets_dir, exist_ok=True)
        os.makedirs(etf_dir, exist_ok=True)
        os.makedirs(raw_degiro, exist_ok=True)
        os.makedirs(decisions_2026, exist_ok=True)
        os.makedirs(history_dir, exist_ok=True)

        # Create sample files
        with open(os.path.join(assets_dir, "SAMPLE_ASSET.md"), "w", encoding="utf-8") as f:
            f.write("# Sample Asset")
        with open(os.path.join(etf_dir, "MSFT.md"), "w", encoding="utf-8") as f:
            f.write("# MSFT Holding")
        with open(os.path.join(etf_dir, "Holdings_Overview.md"), "w", encoding="utf-8") as f:
            f.write("# Holdings Overview")
        with open(os.path.join(raw_degiro, "sample_degiro.csv"), "w", encoding="utf-8") as f:
            f.write("mock,csv,data")
        with open(os.path.join(decisions_2026, "2026-09-01_MSFT_BUY.md"), "w", encoding="utf-8") as f:
            f.write("# Decision")
        with open(os.path.join(tmp_dir, "20_Decisions", "2026-Q3_Retrospective.md"), "w", encoding="utf-8") as f:
            f.write("# Retrospective")
        with open(os.path.join(history_dir, "portfolio.csv"), "w", encoding="utf-8") as f:
            f.write(
                "date,ticker,name,value_base,current_price,pe_ratio,quantity,portfolio\n2026-09-19,MSFT,Microsoft,16575,425,,10,aggressive\n"
            )

        # 2. Run purge
        counts = purge_sample_data(tmp_dir)
        assert counts["assets"] == 1
        assert counts["etf_holdings"] == 1
        assert counts["raw_files"] == 1
        assert counts["decisions"] == 2

        # 3. Verify files state
        assert not os.path.exists(os.path.join(assets_dir, "SAMPLE_ASSET.md"))
        assert os.path.exists(os.path.join(assets_dir, ".gitkeep"))

        assert not os.path.exists(os.path.join(etf_dir, "MSFT.md"))
        assert os.path.exists(os.path.join(etf_dir, "Holdings_Overview.md"))

        assert not os.path.exists(os.path.join(raw_degiro, "sample_degiro.csv"))
        assert os.path.exists(os.path.join(raw_degiro, ".gitkeep"))

        assert not os.path.exists(os.path.join(decisions_2026, "2026-09-01_MSFT_BUY.md"))
        assert not os.path.exists(os.path.join(tmp_dir, "20_Decisions", "2026-Q3_Retrospective.md"))

        # Verify portfolio.csv has only header
        with open(os.path.join(history_dir, "portfolio.csv"), encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        assert "date,ticker,name,value_base" in lines[0]


def test_scaffold_target_vault_clean():
    with tempfile.TemporaryDirectory() as tmp_target:
        ok = scaffold_target_vault(
            source_vault=VAULT_ROOT,
            target_vault=tmp_target,
            clean=True,
            force=True,
            interactive=False,
        )
        assert ok is True

        # Verify system components copied
        assert os.path.exists(os.path.join(tmp_target, "99_System", "Scripts"))
        assert os.path.exists(os.path.join(tmp_target, "99_System", "Templates"))
        assert os.path.exists(os.path.join(tmp_target, "99_System", "Views"))

        # Verify tests are strictly decoupled and NOT copied
        assert not os.path.exists(os.path.join(tmp_target, "99_System", "Tests"))

        # Verify .obsidian copied
        assert os.path.exists(os.path.join(tmp_target, ".obsidian"))

        # Verify core dashboards copied
        assert os.path.exists(os.path.join(tmp_target, "Overview.md"))
        assert os.path.exists(os.path.join(tmp_target, "Welcome.md"))
        assert os.path.exists(os.path.join(tmp_target, "Health.md"))

        # Verify clean mode: Holdings_Overview copied, but no sample assets
        assert os.path.exists(os.path.join(tmp_target, "10_Finance", "ETF_Holdings", "Holdings_Overview.md"))
        assets_dir = os.path.join(tmp_target, "10_Finance", "Assets")
        md_assets = [f for f in os.listdir(assets_dir) if f.endswith(".md")] if os.path.exists(assets_dir) else []
        assert len(md_assets) == 0

        # Verify portfolio.csv has header
        csv_path = os.path.join(tmp_target, "10_Finance", "History", "portfolio.csv")
        assert os.path.exists(csv_path)
        with open(csv_path, encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("date,ticker,name,value_base")


def test_init_vault_full_flow():
    with tempfile.TemporaryDirectory() as tmp_target:
        ok = init_vault(
            target_vault=tmp_target,
            interactive=False,
            clean=True,
            force=True,
        )
        assert ok is True
        assert os.path.exists(os.path.join(tmp_target, ".vault_version"))
        assert os.path.exists(os.path.join(tmp_target, ".env"))
        assert os.path.exists(os.path.join(tmp_target, "config.yaml"))


def test_run_cli_init_parser():
    import run

    parser = run.build_parser()
    args = parser.parse_args(["--init", "--clean", "--target", "../some_vault", "--force"])
    assert args.action_init is True
    assert args.clean is True
    assert args.target == "../some_vault"
    assert args.force is True


def test_init_cli_parser():
    import init

    with patch("init.init_vault", return_value=True) as mock_init:
        with patch.object(
            sys, "argv", ["init.py", "--clean", "--target", "../some_vault", "--force", "--non-interactive"]
        ):
            exit_code = init.main()
            assert exit_code == 0
            mock_init.assert_called_once_with(
                target_vault="../some_vault",
                interactive=False,
                clean=True,
                force=True,
            )


def test_prompt_exante_mode():
    from init_vault import prompt_exante_mode

    with patch("builtins.input", return_value=""):
        assert prompt_exante_mode() == "csv"

    with patch("builtins.input", return_value="1"):
        assert prompt_exante_mode() == "csv"

    with patch("builtins.input", return_value="csv"):
        assert prompt_exante_mode() == "csv"

    with patch("builtins.input", return_value="2"):
        assert prompt_exante_mode() == "api"

    with patch("builtins.input", return_value="API"):
        assert prompt_exante_mode() == "api"


def test_prompt_exante_api_credentials():
    from init_vault import prompt_exante_api_credentials

    with tempfile.TemporaryDirectory() as tmp_dir:
        env_path = os.path.join(tmp_dir, ".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("EXANTE_API_KEY=your_exante_application_id\nEXANTE_API_SECRET=your_exante_shared_key\n")

        # 1. Skip when user presses Enter on API key
        with patch("builtins.input", return_value=""):
            assert prompt_exante_api_credentials(env_path) is False

        # 2. Fill credentials for Demo environment
        with patch("builtins.input", side_effect=["app-123", "secret-456", "ACC.001", "2"]):
            assert prompt_exante_api_credentials(env_path) is True

        with open(env_path, encoding="utf-8") as f:
            env_content = f.read()

        assert "EXANTE_API_KEY=app-123" in env_content
        assert "EXANTE_API_SECRET=secret-456" in env_content
        assert "EXANTE_ACCOUNT_ID=ACC.001" in env_content
        assert "EXANTE_API_URL=https://api-demo.exante.eu" in env_content


def test_brokers_step_exante_mode_api_when_exante_selected():
    from platforms.base import PlatformRegistry

    with tempfile.TemporaryDirectory() as tmp_target:
        # Select Exante in brokers step -> prompt_exante_mode returns 'api', skip API key prompt
        with patch("builtins.input", side_effect=["exante", "api", ""]):
            ok = init_vault(
                target_vault=tmp_target,
                interactive=True,
                step="brokers",
            )
        assert ok is True
        exante_platform = PlatformRegistry.get("exante", base_dir=tmp_target)
        assert exante_platform is not None
        assert exante_platform.get_config().enabled is True
        assert exante_platform.get_config().default_mode == "api"

        PlatformRegistry.set_platform_mode("exante", "csv", base_dir=tmp_target)
        assert exante_platform.get_config().default_mode == "csv"


def test_brokers_step_skips_exante_mode_when_exante_not_selected():
    from platforms.base import PlatformRegistry

    with tempfile.TemporaryDirectory() as tmp_target:
        with (
            patch("builtins.input", return_value="degiro"),
            patch("init_steps.step_02_brokers.prompt_exante_mode") as mock_exante_prompt,
        ):
            ok = init_vault(
                target_vault=tmp_target,
                interactive=True,
                step="brokers",
            )
        assert ok is True
        mock_exante_prompt.assert_not_called()
        exante_platform = PlatformRegistry.get("exante", base_dir=tmp_target)
        assert exante_platform is not None
        assert exante_platform.get_config().enabled is False


def test_init_step_registry_and_aliases():
    from init_vault import InitStepRegistry, list_init_steps

    steps = list_init_steps()
    assert len(steps) == 6
    step_ids = [s["step_id"] for s in steps]
    assert step_ids == [
        "vault_mode",
        "brokers",
        "localization",
        "model_portfolios",
        "agent_profile",
        "diagnostics",
    ]

    # Lookup by number, canonical id, and hyphenated alias
    assert InitStepRegistry.get("1").step_id == "vault_mode"
    assert InitStepRegistry.get("brokers").step_id == "brokers"
    assert InitStepRegistry.get("platforms").step_id == "brokers"
    assert InitStepRegistry.get("model-portfolios").step_id == "model_portfolios"
    assert InitStepRegistry.get("agent-profile").step_id == "agent_profile"
    assert InitStepRegistry.get("nonexistent") is None


def test_degiro_substep_and_default_portfolio():
    from init_vault import prompt_degiro_portfolio
    from platforms.base import PlatformRegistry

    with patch("builtins.input", return_value=""):
        assert prompt_degiro_portfolio() == "Aggressive"

    with patch("builtins.input", return_value="1"):
        assert prompt_degiro_portfolio() == "Aggressive"

    with patch("builtins.input", return_value="2"):
        assert prompt_degiro_portfolio() == "Long term"

    with tempfile.TemporaryDirectory() as tmp_target:
        ok = init_vault(target_vault=tmp_target, interactive=False, clean=True, force=True)
        assert ok is True

        PlatformRegistry.set_platform_default_portfolio("degiro", "Long term", base_dir=tmp_target)
        degiro_platform = PlatformRegistry.get("degiro", base_dir=tmp_target)
        assert degiro_platform is not None
        assert degiro_platform.get_config().default_portfolio == "Long term"


def test_model_portfolios_step_presets_and_single_stock_cap():
    from init_vault import configure_model_portfolios
    from model.config import load_vault_config

    with tempfile.TemporaryDirectory() as tmp_target:
        ok = init_vault(target_vault=tmp_target, interactive=False, clean=True, force=True)
        assert ok is True

        # Configure Conservative Multi-Asset preset with 12.0% single stock cap
        preset, cap = configure_model_portfolios(
            tmp_target,
            interactive=False,
            preset_id="conservative",
            max_single_stock_pct=12.0,
        )
        assert preset == "conservative"
        assert cap == 12.0

        cfg = load_vault_config(base_dir=tmp_target, force_refresh=True)
        long_term_targets = {t.target: t.weight_pct for t in cfg.model_portfolios["long_term"].layers.asset_classes}
        assert long_term_targets == {
            "Equities": 39.0,
            "Real Estate": 30.0,
            "Bonds": 26.0,
            "Gold": 5.0,
        }
        assert cfg.user_profile.max_single_stock_pct == 12.0
        assert cfg.alerts.allocation_drift.max_portfolio_weight_pct == 12.0


def test_single_step_reconfiguration_via_init_vault():
    from model.config import load_vault_config

    with tempfile.TemporaryDirectory() as tmp_target:
        # Run only Step 4 (model_portfolios) on a fresh directory
        ok = init_vault(
            target_vault=tmp_target,
            interactive=False,
            step="model-portfolios",
            preset_id="aggressive_growth",
        )
        assert ok is True
        assert os.path.exists(os.path.join(tmp_target, "config.yaml"))

        cfg = load_vault_config(base_dir=tmp_target, force_refresh=True)
        lt_targets = {t.target: t.weight_pct for t in cfg.model_portfolios["long_term"].layers.asset_classes}
        assert lt_targets["Real Estate"] == 30.0
        assert lt_targets["Gold"] == 5.0
        assert lt_targets["Equities"] == 58.5
        assert lt_targets["Bonds"] == 6.5

        # Invalid step returns False
        assert init_vault(target_vault=tmp_target, interactive=False, step="invalid_step") is False


def test_prompt_step_selection_menu():
    from init_vault import prompt_step_selection_menu

    with patch("builtins.input", return_value=""):
        assert prompt_step_selection_menu() is None

    with patch("builtins.input", return_value="A"):
        assert prompt_step_selection_menu() is None

    with patch("builtins.input", return_value="2"):
        assert prompt_step_selection_menu() == "brokers"

    with patch("builtins.input", return_value="model-portfolios"):
        assert prompt_step_selection_menu() == "model_portfolios"
