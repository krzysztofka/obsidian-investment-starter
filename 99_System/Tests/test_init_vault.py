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
    _update_localization_in_config,
    configure_localization,
    prompt_base_currency_selection,
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
