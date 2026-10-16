# Configurable Base Currency & Value Base Migration

## Context
The system historically hardcoded Polish Złoty (PLN) as the sole portfolio currency across asset note frontmatters (`value_pln`), historical timeline records (`portfolio.csv`), model portfolio thresholds (`min_trade_amount_pln`), and DataviewJS dashboards. To support international investors and multi-currency wealth portfolios without codebase forks, the portfolio requires a user-configurable base currency set during vault bootstrapping.

## Decision
We decided to:
1. Introduce a top-level `localization:` block in `config.yaml` with `base_currency`, `currency_symbol`, `symbol_position`, and `supported_currencies`.
2. Standardize asset valuation to `value_base` across asset frontmatter notes and `10_Finance/History/portfolio.csv`, renaming `min_trade_amount_pln` to `min_trade_amount` cleanly without redundant code fallbacks.
3. Migrate existing PLN vaults in `patch_0_9_to_0_10.py` by default-configuring `PLN`, duplicating `value_pln` into `value_base`, and updating the `portfolio.csv` column header.
4. Generalize currency exchange resolution in `integrations/yfinance/service.py` to universal cross pairs with triangular routing via USD/EUR and NBP/ECB integrations.

## Consequences
- Asset notes and history records use canonical `value_base` regardless of whether base currency is PLN, EUR, USD, GBP, or CHF.
- DataviewJS views dynamically read `base_currency` and `currency_symbol` from `config.yaml`, eliminating hardcoded "PLN" strings in UI components.
- Sanity checks and platform parsers validate `value_base` as the primary valuation metric.
