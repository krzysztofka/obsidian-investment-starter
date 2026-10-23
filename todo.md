# Project Roadmap & Backlog (TODO)

## 🏦 Milestone: v0.13 XTB Broker Integration (API & CSV)

- [ ] **XTB Platform Extension (`99_System/Scripts/platforms/xtb.py`):**
  - [ ] Register `xtb` platform in `PlatformRegistry` with support for both `csv` and `api` import modes (`default_mode` in `config.yaml`).
  - [ ] Configure `00_Raw/xtb/` raw export directory and sample statement file (`00_Raw/xtb/sample_xtb.csv`).
- [ ] **XTB CSV / Statement Export Parser:**
  - [ ] Parse XTB xStation 5 exported statements (open positions & multi-currency cash balances).
  - [ ] Map XTB ticker symbols (e.g., `CDR.PL`, `MSFT.US`, `VWCE.DE`) and ISINs to canonical vault tickers and Yahoo Finance symbols.
  - [ ] Support stale position cleanup and automatic asset note enrichment (`10_Finance/Assets/`).
- [ ] **XTB API Integration (`99_System/Scripts/integrations/xtb/`):**
  - [ ] Implement XTB API client for live synchronization of open positions and account cash balances without manual file exports.
  - [ ] Support `.env` credentials (`XTB_USER_ID`, `XTB_PASSWORD`, `XTB_ACCOUNT_TYPE` / environment).
  - [ ] Add connectivity probe for XTB API in `health_check.py` (enabled when `xtb` platform is active in `api` mode).
- [ ] **Interactive Vault Onboarding & Sub-step (`step_02_brokers.py`):**
  - [ ] Add XTB per-broker configuration sub-step triggered only when `xtb` is selected during platform initialization (choosing `CSV` vs `API` mode, target portfolio, and optional `.env` credentials).
- [ ] **Automated Testing & Migration Patch (`0.12.0` -> `0.13.0`):**
  - [ ] Unit tests for XTB CSV parser, API client mocks, and onboarding sub-step (`99_System/Tests/platforms/test_xtb.py`).
  - [ ] Sequential migration patch `patch_0_12_to_0_13.py` non-destructively merging `xtb` platform config into `config.yaml`.

---

## 🏠 Milestone: v0.14 Real Estate Valuation & Property Management

- [ ] **Property Parameterization & Schema Expansion:**
  - [ ] Extended frontmatter schema for real estate assets: area (`area_sqm`), floor (`floor`, `total_floors`), rooms, year built, building type, condition, garage/parking, storage room.
  - [ ] Financial metrics: purchase price/date, monthly rental income, admin fees, property taxes, mortgage details (principal remaining, monthly payment, LTV), net equity.
- [ ] **Real Estate Valuation Engine:**
  - [ ] Parametric square meter valuation model: $\text{Value} = (\text{area\_sqm} \times \text{price\_per\_sqm}) + \text{parking} + \text{storage}$.
  - [ ] Optional hedonic scoring model (adjustments for floor, elevator, terrace/balcony, building age, condition).
  - [ ] Automated valuation updates in `update_currencies.py` / `run.py --update-rates`.
- [ ] **Market Data & Regional Price Indices (Optional Sync):**
  - [ ] Integration with regional Polish real estate market data / NBP quarterly transaction price reports / Otodom / Zametr indices.
  - [ ] Automated or semi-automated `price_per_sqm` benchmarking by city and district.
- [ ] **Real Estate Dashboard & Yield Analytics:**
  - [ ] Dedicated real estate card view and ROI / rental yield calculator in DataviewJS (Gross Yield, Net Yield, Cash-on-Cash Return, Net Equity).
  - [ ] Real Estate template (`99_System/Templates/real_estate_template.md`).

---

## 🔮 Backlog & Future Enhancements

### 📊 Ideas, Watchlist & Macro Research

- [ ] Automatic Watchlist refresh & candidate generator via OpenBB / Finviz.
- [ ] Valuation catalyst notes explaining why scanners flagged specific tickers as undervalued.
- [X] `10_Finance/Macro.md` tracking central bank interest rates (Fed, ECB, NBP), CPI inflation, unemployment, and yield curves (10Y-2Y spread).
- [ ] FRED API integration (`fredapi`) for advanced macro data (M2 money supply, Fed balance sheet, initial jobless claims).
- [ ] Interactive Dataview / DataviewJS macro regime widget for `Overview.md` and `Welcome.md`.
- [ ] Investment reasoning & thesis documentation for all existing portfolio assets.

### 🔌 External Integrations

- [ ] Morningstar ratings & risk metrics via RapidAPI / OpenBB fallback.
- [ ] Technical analysis indicators via `tradingview-ta` (e.g., 200-day SMA trend alignment).
- [ ] News & RSS sentiment feeds (Seeking Alpha, MacroTrends).

---

## ✅ Completed Milestones

- [X] **v0.12 Interactive Model Portfolio Configuration & Drift Checking:**
  - [X] **Interactive Model Portfolio Configuration Wizard (`setup_model_portfolios.py` / CLI):**
    - [X] Interactive CLI wizard to inspect, configure, and modify target allocations for each portfolio bucket (*Safety Net*, *Long Term*, *Aggressive*).
    - [X] Command runner support: `python run.py --setup-model-portfolios`, `python init.py --step model_portfolios`, and onboarding integration into `step_04_model_portfolios.py`.
  - [X] **Layered Target Allocation Builder:**
    - [X] Guided configuration across allocation layers: `asset_classes`, `sectors`, and specific `assets`.
    - [X] Pre-built portfolio presets and starter templates based on risk profiles including Real Estate (30%) and Gold (5%) in *Long Term* (`step_04_model_portfolios.py`).
    - [X] Custom allocation editor with live weight calculation and flexible layer sum validation (`0 < sum <= 100%`, allowing unconstrained remainder).
  - [X] **Rebalance Strategy & Threshold Corridors Tuning:**
    - [X] Interactive selection of rebalance strategy (`inflow_first` cash-flow DCA vs `full_rebalance`).
    - [X] Setting tolerance corridors (`tolerance_band_pct`) and minimum trade floors (`min_trade_amount`) with portfolio-level defaults and per-target overrides.
  - [X] **Standalone Model Portfolio Drift Checker (`check_model_portfolios.py` / `run.py --rebalance`):**
    - [X] Portfolio-level drift evaluation script (`python 99_System/Scripts/check_model_portfolios.py` and `python run.py --rebalance`, integrated into `python run.py --all`).
    - [X] Evaluate only configured targets against 100% of portfolio bucket `value_base` (unmodeled holdings included in total value denominator without false warnings).
    - [X] Ignore empty portfolios (`total_value == 0`) and ignore corridor breaches smaller than `min_trade_amount`.
    - [X] Emit structured `WARN` alerts per portfolio detailing breached target, actual % vs target % ± corridor `[min–max]`, drift from target, breach beyond corridor, and Base Currency delta (aligned across CLI, `rebalance_status/view.js`, and `Alerts.md`).
  - [X] **Configuration Validation, Diff Preview & Safe Persistence:**
    - [X] Interactive preview of changes and visual diff before writing to `config.yaml`.
    - [X] Atomic and safe YAML serialization preserving formatting, comments, and existing user settings.
    - [X] Pydantic schema validation (`ModelPortfolioConfig` / `ModelPortfolioLayers` in `99_System/Scripts/model/config.py`).
  - [X] **Sequential Migration Patch (`0.11.0` -> `0.12.0`):**
    - [X] Migration patch `patch_0_11_to_0_12.py` ensuring configuration schema backward-compatibility and version bump.

- [X] **v0.11 Modular Step-by-Step Vault Initialization & Reconfiguration Engine:**
  - [X] **Modular Initialization Step Architecture (`99_System/Scripts/init_steps/`):**
    - [X] Decoupled `init_vault.py` into 6 discrete, registered steps (`InitStepRegistry` & `InitContext`):
      1. `vault_mode`: Clean Vault vs Demo Vault mode & core scaffolding.
      2. `brokers`: Platform selection + per-broker configuration sub-steps (Degiro default portfolio, Exante CSV/API & credentials).
      3. `localization`: Base currency & symbol formatting (`localization:`).
      4. `model_portfolios`: Model portfolio multi-asset presets (including Real Estate 30% & Gold 5% in *Long Term*) + single-stock concentration cap (`max_single_stock_pct` synced across `user_profile` and `alerts.allocation_drift`).
      5. `agent_profile`: Investor risk profile, tax sensitivity, profit harvesting, retirement account priority, and optional AI research credentials (`FINNHUB_API_KEY`).
      6. `diagnostics`: Python dependency verification & external integration connectivity probe.
  - [X] **Standalone Step Reconfiguration (`--step` & Interactive Menu):**
    - [X] CLI support for running any single step in isolation (`python init.py --step <step>` / `python run.py --init --step <step>` / `--list-steps`).
    - [X] Interactive reconfiguration menu when `init.py` is launched on an already-initialized vault.
  - [X] **Sequential Migration Patch (`0.10.0` -> `0.11.0`):**
    - [X] Added `patch_0_10_to_0_11.py` synchronizing modular initialization steps and bumping `.vault_version` to `0.11.0`.

- [X] **v0.10 Multi-Currency & Localization:**
  - [X] **Configurable Base Portfolio Currency (`config.yaml`):**
    - [X] Add `localization:` setting to `config.yaml` and Pydantic model (`LocalizationConfig` / `VaultConfig`), defaulting to `PLN` with support for `EUR`, `USD`, `GBP`, `CHF` (and custom ISO-4217 codes).
    - [X] Support custom base currency symbol and display formatting options (e.g., `currency_symbol: "zł"`, `symbol_position: "suffix"`).
  - [X] **Universal FX Conversion Engine (`integrations/yfinance.py` & `update_currencies.py`):**
    - [X] Generalize FX rate fetching to support arbitrary cross pairs ($Quote \to Base$) via Yahoo Finance direct, inverse, and triangular cross pairs.
    - [X] Implement triangular FX conversion when direct cross-pairs are unavailable (e.g. via USD intermediary).
    - [X] Multi-currency shared caching to eliminate redundant FX network calls during batch valuation.
  - [X] **Asset Schema & Vault Frontmatter Migration:**
    - [X] Introduce `value_base` in asset frontmatter representing valuation in the configured base currency.
    - [X] Maintain seamless backward compatibility for existing `value_pln` fields across note templates and scripts.
    - [X] Support multi-currency unallocated broker/bank cash holdings.
  - [X] **DataviewJS Dashboards & Chart Views Adaptation:**
    - [X] Update DataviewJS views (`Overview.md`, `Portfolio_performance.md`, `rebalance_status`, `alert_banner`, `Safety_portfolio.md`, `Long_term_portfolio.md`, `Aggressive_portfolio.md`, `Alerts.md`) to dynamically read `base_currency` and formatting from config rather than hardcoding `PLN`.
    - [X] Adapt performance chart tooltips, tables, and headers to display the configured portfolio currency.
  - [X] **Localization & Interactive Onboarding (`init.py` / `init_vault.py`):**
    - [X] Interactive prefix auto-completion prompt (e.g. `P` -> PLN, `E` -> EUR, `U` -> USD, `C` -> disambiguation menu).
    - [X] Configurable symbol position, currency codes, and custom ISO-4217 inputs.
  - [X] **Historical Timeline & Archival Compatibility:**
    - [X] Standardize `portfolio.csv` snapshot recording and archival policies (`retention.py`, `update_portfolio.py`) to support `value_base`.
  - [X] **Sequential Migration Patch (`0.9.0` -> `0.10.0`):**
    - [X] Non-destructively merges `localization:` into downstream `config.yaml`.
    - [X] Renames `min_trade_amount_pln` to `min_trade_amount` in `config.yaml`.
    - [X] In-place backfill of `value_base` in existing `10_Finance/Assets/*.md` notes.
    - [X] Updates `portfolio.csv` header to `value_base`.

- [X] **v0.9 Investment Strategy, Model Portfolios & AI Rebalance Advisor:**
  - [X] **Model Portfolio Configuration (`config.yaml`):**
    - [X] Target allocation schema per portfolio (*Safety Net*, *Long Term*, *Aggressive*): by asset class, dominant sector, or specific key assets.
    - [X] Rebalance tolerance bands (corridors, e.g. $\pm 5\%$) and minimum trade thresholds (`min_trade_amount_pln`) to eliminate costly micro-transactions.
    - [X] Strategy preference definition (e.g. `inflow_first` cash-flow rebalancing vs `full_rebalance`).
  - [X] **Investor Profile & Rebalancing Setup (`config.yaml` & `init.py`):**
    - [X] Add `user_profile:` schema to `config.yaml` and Pydantic model (`UserProfileConfig` in `model/config.py`): risk tolerance, single stock cap, tax sensitivity, and profit harvesting rules.
    - [X] Interactive Investor Profile step in `init_vault.py` (`init.py`) to configure risk profile, tax preference, and allocation boundaries during vault setup.
  - [X] **In-Note Rebalance & Drift Alerting Dashboard (`rebalance_status`):**
    - [X] Dedicated DataviewJS view `99_System/Views/rebalance_status` embedded in `Aggressive_portfolio.md`, `Long_term_portfolio.md`, and `Safety_portfolio.md`.
    - [X] Live calculation of actual weights vs target corridors ($Target \pm Tolerance\%$) and PLN deltas.
    - [X] Status badges (`🟢 Balanced`, `⚠️ Overweight`, `⚠️ Underweight`) flagging assets/classes that breached thresholds.
    - [X] Graceful fallback note (`> [!NOTE] ℹ️ Model portfolio targets are not configured for this bucket`) when a portfolio has no configured targets.
  - [X] **AI Portfolio & Rebalance Advisor Skill (`.agents/skills/rebalance-advisor`):**
    - [X] Dedicated project workspace skill loaded on demand when the user requests rebalancing assistance.
    - [X] Cost and friction-aware rebalance proposals (factoring in 19% Belka tax drag on taxable brokers vs 0% on IKE/IKZE, EDO early redemption, single stock limits).
    - [X] Interactive proposal & approval loop: AI queries for operational context (e.g., fresh cash for DCA vs trimming existing positions), presents concrete trade proposals, and asks for approval.
    - [X] Automated Decision Drafting: Upon user approval, automatically writes decision notes into `20_Decisions/YYYY/` via `decision_template.md`, instantly populating the `Open Decisions & Pending Orders` view.

- [X] **v0.8 System Health Checks, Sanity Diagnostics & Downstream Decoupling:**
  - [X] **Integrations Health Check & Connectivity Diagnostics (`health_check.py` / CLI):**
    - [X] Dedicated diagnostic runner script and CLI flag (`python run.py --health` or `python 99_System/Scripts/health_check.py`).
    - [X] Automated connectivity and response probes for all external integrations (`yfinance`, `exante`, `finnhub`, `justetf`, `nbp`, `eurostat`, `stooq`, `openbb`).
    - [X] Visual CLI diagnostic report with latency metrics, status badges (✅ OK / ⚠️ WARN / ❌ FAIL), and troubleshooting hints.
  - [X] **Vault Sanity & Data Integrity Checker (`sanity_check.py` / CLI):**
    - [X] Frontmatter validation for all notes in `10_Finance/Assets/*.md` (`value_pln`, `portfolio`, `currency`, numeric ranges, ticker collisions).
    - [X] Historical timeline integrity check for `10_Finance/History/portfolio.csv` with automated `--fix` sorting & deduplication.
    - [X] Broker exports validation in `00_Raw/` and `.env` environment key verification.
  - [X] **Downstream Test Decoupling & Vault Cleanliness (Starter vs Downstream):**
    - [X] Exclude `99_System/Tests/` from patch synchronization to downstream personal vaults (`trader`).
    - [X] In `patch_0_7_to_0_8.py`, automatically prune `99_System/Tests/` and `.pytest_cache/` from downstream vaults.
    - [X] Automated test suite expanded to 106 passing unit and mock tests.

- [X] **v0.7 Code Quality, Testing & Reliability:**
  - [X] **Automated Test Suite (`pytest` - 86 Passing Tests):**
    - [X] Dedicated test package for platform extensions (`99_System/Tests/platforms/`).
    - [X] Unit tests for all broker platform parsers (`PKO BP`, `mBank IKE/IKZE`, `Degiro`, `Exante`).
    - [X] Unit tests for Platform Registry, aliases, path detection, and dynamic enable/disable.
    - [X] Unit tests for Vault Patch Engine and Sequential Migration System (`99_System/Tests/test_patch.py`).
    - [X] Unit tests for Rich progress and multi-threaded processing (`99_System/Tests/test_rich_progress.py`).
    - [X] Unit tests for currency conversion and PLN portfolio valuation logic (`99_System/Tests/test_update_currencies.py`).
    - [X] Unit tests for Alert Rules Engine evaluation & tagging (`99_System/Tests/alerts/test_rules.py`, `test_engine.py`).
    - [X] Unit tests for portfolio historical snapshot timeline and CSV handling (`99_System/Tests/history/test_update_portfolio.py`).
    - [X] Unit tests for macroeconomic dashboard engine and Jinja2 rendering (`99_System/Tests/macro/test_sync_macro.py`).
    - [X] Unit tests for modular platform storage persistence and template rendering (`99_System/Tests/platforms/test_storage.py`, `test_template.py`).
    - [X] Mock tests for external API enrichers (`yfinance`, `finnhub`, `justetf`, `stooq`, `nbp`, `multi_source`).
    - [X] Unit tests for Data Retention & History Archival policies (`99_System/Tests/history/test_retention.py`).
  - [X] **Codebase Architecture & System Deduplication (Review #1):**
    - [X] Single source of truth configuration: unified root `config.yaml` and eliminated duplicate `99_System/config.yaml`.
    - [X] Standardized all modules to use canonical `load_vault_config()` Pydantic loader.
    - [X] Removed obsolete secondary CLI runner (`99_System/Scripts/run.py`).
    - [X] Standardized DataviewJS view subdirectory structure (`99_System/Views/<view>/view.js`) and created `runner_widget/view.js`.
    - [X] Standardized legacy sample asset notes to canonical `asset_template.md` frontmatter schema.
    - [X] Modularized monolithic `platforms/common.py` into `platforms/storage.py` and `platforms/template.py`.
    - [X] Declared missing `jinja2>=3.1.0` dependency in `pyproject.toml` and `requirements.txt`.
    - [X] Structured logging utility (`99_System/Scripts/logging_util.py`) with `rich.logging.RichHandler`.
  - [X] **Type Hints, Linting & Formatting:**
    - [X] Full static typing and type annotations across all scripts in `99_System/Scripts/` (78 source files clean in `mypy`).
    - [X] Standardized linter & code formatter configuration (`ruff`).
  - [X] **Data Retention & History Archival (`retention.py`):**
    - [X] Portfolio history archival: retains daily entries for up to 2 years, archiving older records to partitioned yearly files (`10_Finance/History/archive/history-archive-YYYY.csv`).
    - [X] Boundary baseline preservation: carries over active positions at cutoff date to maintain continuous valuation charts in DataviewJS.
    - [X] Ephemeral raw broker export rotation: archives or prunes raw exports older than 1 year (`00_Raw/archive/`) with SHA-256 deduplication and collision disambiguation.
    - [X] Exclusion pattern support preserving sample files (`sample_*.*`), `.gitkeep`, and research directories.
    - [X] Unified CLI integrations (`python run.py --archive` with `--dry-run` and automatic triggers on `import` / `history`).
  - [X] **Resilient Error Handling & Logging:**
    - [X] Structured logging utility (`logging_util.py`) and informative error handling.
    - [X] Input validation for manual and imported note frontmatters (Pydantic `Asset` & `VaultConfig` models).
  - [X] **Sequential Version Migration (`patch_0_6_to_0_7.py`):**
    - [X] Automated upgrade path from v0.6.0 to v0.7.0 preserving all private user data and custom configurations.

- [X] **v0.6 Template Starter Architecture & Inverted Synchronization:**

  - [X] **Invert Template Generation Flow:**
    - Transitioned template repository (`obsidian-investment-starter`) to the canonical upstream starter repository.
    - Template acts as standalone starter that distributes and installs changes, bugfixes, and features into downstream user vaults.
  - [X] **Starter Patcher & Vault Update Engine (`patch.py` / `99_System/Scripts/patch/` / CLI):**
    - Sequential version patching engine (`PatchEngine`) with automated migrations (`patch_0_5_to_0_6.py`).
    - Safe merge protecting personal data (`10_Finance/Assets/`, `00_Raw/`, `20_Decisions/`, `portfolio.csv`, local `.env`, and custom configurations).
    - CLI runner commands: `python patch.py` and `python run.py --sync-vault <target>`.
    - Dry-run mode (`--dry-run`) to preview updates.
  - [X] **Project Scaffolding & Initial Setup (`init.py` / `init_vault.py`):**
    - Step-by-step setup script configuring directories, `.env`, `.gitignore`, config, and version tracking (`.vault_version`).
  - [X] **PKO BP Sample Data:**
    - Standard retail inflation treasury bond dataset in `00_Raw/pkobp/sample_pkobp.xls`.
    - Sanitized documentation references to private account IDs.
- [X] **v0.5 Concurrent Asset Sync & Performance:**

  - [X] **Parallel Asset Enrichment & Pipeline Execution:**
    - [X] Concurrent asset enrichment in `platforms/common.py` and `import_assets.py` using `ThreadPoolExecutor` (auto-detects CPU hardware threads count).
    - [X] Parallelize external API & scraping queries across data providers (`yfinance`, `finnhub`, `justetf`, `ishares`, `vanguard`, `vaneck`).
    - [X] Concurrent batch processing for ETF top holdings decomposition and cross-exposure sync (`sync_etf_holdings.py`).
    - [X] Concurrent currency exchange rates fetching and portfolio valuation in `update_currencies.py`.
  - [X] **Automated Macroeconomic Synchronization (`sync_macro.py`):**
    - [X] Automated fetcher for central bank rates, inflation, and bond yields (Yahoo Finance `^TNX`, `^IRX`, `GC=F`, `BZ=F`, `HG=F`, `SI=F`, `^VIX`, Eurostat & NBP Web API for Polish rates/CPI/yields).
    - [X] Automatic frontmatter and indicator table updates in `10_Finance/Macro.md`.
    - [X] CLI integration: `python run.py --macro` and inclusion in `python run.py --all`.
    - [X] Macro risk indicators in Alert Rules Engine (e.g., `#alert/macro_inverted_yield_curve` and spread compression).
  - [X] **Rate Limiting, Throttling & Resilience:**
    - [X] Configurable worker concurrency limits (pool size) in `config.yaml` / CLI flags (`-w`, `--workers`).
    - [X] Provider-specific throttling & polite pacing (avoid HTTP 429 Too Many Requests on Finnhub, Yahoo Finance, and JustETF).
    - [X] Thread-safe retry policies with exponential backoff and jitter.
  - [X] **Thread-Safe Note Writing & Shared State:**
    - [X] Atomic and thread-safe file writing for asset notes (`10_Finance/Assets/`) and ETF holdings (`10_Finance/ETF_Holdings/`).
    - [X] Shared memory cache for FX rates, quotes, and metadata to eliminate redundant downloads across concurrent workers.
  - [X] **CLI UX & Performance Observability:**
    - [X] Real-time concurrent progress indicators / status reporting (e.g. `rich` or `tqdm`) during imports and sync.
    - [X] Pipeline execution timing metrics and speedup benchmarks in `run.py`.
- [X] **v0.4 Git Public Template & Sanitization:**

  - [X] Comprehensive `.gitignore` covering `00_Raw/*`, `.env`, `.obsidian` session files, and Python cache.
  - [X] Provide `.env.example` with documented environment variable keys.
  - [X] Anonymized sample CSV exports: `00_Raw/Degiro/sample_degiro.csv`, `00_Raw/Exante/sample_exante.csv`, `00_Raw/mBM/sample_ike.csv`, `00_Raw/mBM/sample_ikze.csv`.
  - [X] Demo asset notes in `10_Finance/Assets/` replacing private real estate and personal bank accounts.
  - [X] Sample investment decision note demonstrating thesis and pre-mortem workflow.
  - [X] Export workflow script (`99_System/Scripts/export_template.py` / `run.py --export-template`) for pushing clean templates to GitHub without leaking personal vaults.
  - [X] Comprehensive `README.md` with architecture diagram, screenshots, and quickstart guide.
  - [X] Open-source license (MIT).
- [X] **v0.3 Broker Integrations & Tooling:**

  - [X] **PKO BP Treasury Bonds Integration:**
    - [X] Native parser for PKO BP register status Excel files (`00_Raw/pkobp/StanRachunkuRejestrowego_*.xls`).
    - [X] Rule-based portfolio allocation & split engine (Safety Net vs Long Term rules in `config.yaml`).
    - [X] Bond asset creation with clean frontmatter (`asset_type: bond`, `dominant_sector: Sovereign`, `stooq_ticker: 10ply.b`).
    - [X] Unified CLI support: `python run.py --import --platform pkobp` and auto-detection from file path.
  - [X] **ETF Issuer Integrations:**
    - [X] iShares (official product website URLs & metadata resolution).
    - [X] Vanguard (official US & UK/Europe UCITS profile resolution).
    - [X] VanEck (official UCITS & US ETF catalog & profile resolution).
  - [X] **Unified CLI Runner (`run.py`):**
    - [X] Unified command interface: `--import`, `--update-rates`, `--sync-etfs`, `--alerts`, `--history`.
  - [X] **Exante REST API Integration:**
    - [X] Implement official Exante Client API connector (`platforms/exante_api.py`) using API Key & App Secret.
    - [X] Fetch live account balances and open positions without manual CSV exports.
  - [X] **Degiro Integration:**
    - [X] Robust CSV import with missing asset cleanup.
  - [X] **mBank Biuro Maklerskie (mBM) Integration:**
    - [X] Multi-account support for IKE (`mBM (IKE)`) and IKZE (`mBM (IKZE)`).
- [X] **v0.2 Alert Rules Engine & System Refactoring:**

  - [X] Refactor and organize `todo.md` roadmap.
  - [X] Implement modular Alert Rules Engine in `99_System/Scripts/alerts/`:
    - [X] `BaseAlertRule` interface and `AlertContext` loader.
    - [X] `OvervaluedRule` (`#alert/overvalued` - P/E threshold check).
    - [X] `DelistingRiskRule` (`#alert/delisting_risk` - ETF AUM minimum threshold).
    - [X] `InsiderSellingRule` (`#alert/insider_sell` - Finnhub SEC insider transactions).
    - [X] `AllocationDriftRule` (`#alert/allocation_drift` - single equity portfolio weight limit).
    - [X] `StopLossRule` (`#alert/stop_loss` - price breaching stop loss level).
  - [X] Centralize alert thresholds and toggles in `config.yaml`.
  - [X] Provide CLI runner `python 99_System/Scripts/alerts/engine.py` with standalone scanning and tagging.
  - [X] Update `Alerts.md` and dashboard views (`Overview.md`, portfolio views) to display the new alert categories.
- [X] **v0.1 Core Foundation:**

  - [X] Three-Portfolio Architecture implemented (*Safety Net*, *Long Term*, *Aggressive*) with strict capital silo principles.
  - [X] Multi-source asset enrichment (Yahoo Finance, JustETF, Finnhub).
  - [X] ETF top holdings decomposition and cross-exposure tracking (`sync_etf_holdings.py`).
  - [X] Portfolio performance timeline and Dataview dashboards.
