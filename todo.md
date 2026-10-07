# Project Roadmap & Backlog (TODO)

## ⚡ Current Milestone: v0.7 Code Quality, Testing & Reliability

- [X] **Automated Test Suite (`pytest` - 77 Passing Tests):**
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
  - [X] Full static typing and type annotations across all scripts in `99_System/Scripts/`.
  - [X] Standardized linter & code formatter configuration (`ruff` / `black`).
- [ ] **Data Retention & History Archival:**
  - [ ] Portfolio history archival: retain daily entries for up to 2 years, archiving older records to `history-archive-YYYY.csv`.
  - [ ] Ephemeral raw data rotation: automatically archive or prune raw CSV/Excel exports older than 1 year.
- [X] **Resilient Error Handling & Logging:**
  - [X] Structured logging utility (`logging_util.py`) and informative error handling.
  - [X] Input validation for manual and imported note frontmatters (Pydantic `Asset` & `VaultConfig` models).

---

## 🩺 Milestone: v0.8 Integrations Health Check & Connectivity Diagnostics

- [ ] **Integrations Health Check & Connectivity Diagnostics (`health_check.py` / CLI):**
  - [ ] Dedicated diagnostic runner script and CLI flag (`python run.py --health` or `python 99_System/Scripts/health_check.py`).
  - [ ] Automated connectivity and response probes for all external integrations:
    - [ ] `yfinance`: test price quote and fundamentals retrieval for a sample ticker (e.g. `SPY` / `AAPL`).
    - [ ] `exante`: verify REST API credentials, token generation, and account summary connectivity (simple GET request).
    - [ ] `finnhub`: test API key validity and recommendation consensus probe.
    - [ ] `justetf`: check HTTP reachability and basic profile scraping for a sample ISIN.
    - [ ] `nbp`: test official Table A exchange rate fixing API endpoint.
    - [ ] `eurostat`: test Polish 10Y sovereign yield endpoint.
    - [ ] `stooq`: check quote service accessibility.
    - [ ] `openbb`: verify local environment availability and fallback status.
  - [ ] Visual CLI diagnostic report with latency metrics, status badges (✅ OK / ⚠️ WARN / ❌ FAIL), and troubleshooting hints for missing `.env` keys, rate limits, or network timeouts.

---

## ⚖️ Milestone: v0.9 Investment Strategy, Model Portfolios & AI Rebalance Advisor

- [ ] **Model Portfolio Configuration (`config.yaml`):**
  - [ ] Target allocation schema per portfolio (*Safety Net*, *Long Term*, *Aggressive*): by asset class, dominant sector, or specific key assets.
  - [ ] Rebalance tolerance bands (corridors, e.g. $\pm 5\%$) and minimum trade thresholds (`min_trade_amount_pln`) to eliminate costly micro-transactions.
  - [ ] Strategy preference definition (e.g. `inflow_first` cash-flow rebalancing vs `full_rebalance`).
- [ ] **Cost-Aware Rebalancing & Drift Engine (`rebalance.py` / CLI):**
  - [ ] Calculation engine computing real-time allocation drift (Actual % vs Model Target %) and delta in PLN.
  - [ ] Cash-Flow Rebalancer: calculating optimal capital distribution for new deposits/DCA to close allocation gaps without triggering taxable sales.
  - [ ] CLI command: `python run.py --rebalance` (with `--portfolio <name>` and optional `--deposit <amount_pln>`).
- [ ] **Model vs Actual Dataview Dashboard:**
  - [ ] Visual progress / allocation delta bars in `Overview.md` and dedicated portfolio views.
  - [ ] Drift summary widget highlighting positions exceeding tolerance bands.
- [ ] **AI Portfolio & Rebalance Advisor Skill:**
  - [ ] Portfolio-specific advisor skill / system prompt enforcing the *Strict Capital Silo Rule*.
  - [ ] Asset-specific cost & friction awareness (EDO bond early redemption penalty, physical gold bid-ask spreads, IKE/IKZE annual limit maximization, tax drag on taxable brokers).
  - [ ] Quarterly review integration: automated rebalance recommendations linked with `20_Decisions/YYYY-QN_Retrospective.md` and automated decision drafting via `decision_template.md`.

---

## 🏠 Milestone: v1.0 Real Estate Valuation & Property Management

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

### 🌐 Multi-Currency & Localization

- [ ] Generic base currency configuration (EUR/USD) instead of hardcoded PLN.

---

## ✅ Completed Milestones

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
