"""Step 3: Localization and Base Portfolio Currency Configuration."""

import os
import re

from model.config import DEFAULT_CURRENCY_SYMBOLS

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry


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


@InitStepRegistry.register
class LocalizationStep(BaseInitStep):
    """Step 3: Configure localization and base portfolio currency."""

    step_id = "localization"
    step_number = 3
    title = "Configuring localization & base portfolio currency"
    description = "Configure portfolio base currency (ISO-4217), symbol, and display position."
    aliases = ["currency", "locale", "fx"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)
        base_curr, symbol, pos = configure_localization(ctx.target_dir, interactive=ctx.interactive)
        ctx.base_currency = base_curr
        ctx.currency_symbol = symbol
        ctx.symbol_position = pos
        return True
