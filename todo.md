# Project Roadmap & Backlog (TODO)

## 🚀 Current Milestone: v0.3 Broker Integrations & Tooling
- [x] **ETF Issuer Integrations:**
  - [x] iShares (official product website URLs & metadata resolution).
  - [x] Vanguard (official US & UK/Europe UCITS profile resolution).
  - [x] VanEck (official UCITS & US ETF catalog & profile resolution).
- [x] **Unified CLI Runner (`run.py`):**
  - [x] Unified command interface: `--import`, `--update-rates`, `--sync-etfs`, `--alerts`, `--history`.
- [x] **Exante REST API Integration:**
  - [x] Implement official Exante Client API connector (`platforms/exante_api.py`) using API Key & App Secret.
  - [x] Fetch live account balances and open positions without manual CSV exports.
- [x] **Degiro Integration:**
  - [x] Maintain robust CSV import as primary zero-credential fallback.
  - [x] Evaluate optional read-only connector or headless session fetcher.
- [x] **mBank eMakler Integration:**

---

## 🌍 Milestone: v0.4 Git Public Template & Sanitization
- [x] **Privacy & Security Audit:**
  - [x] Comprehensive `.gitignore` covering `00_Raw/*`, `.env`, `.obsidian` session files, and Python cache.
  - [x] Provide `.env.example` with documented environment variable keys.
- [x] **Sample & Demo Dataset:**
  - [x] Anonymized sample CSV exports: `00_Raw/Degiro/sample_degiro.csv`, `00_Raw/Exante/sample_exante.csv`, `00_Raw/mBM/sample_*.csv`.
  - [x] Demo asset notes in `10_Finance/Assets/` replacing private real estate and personal bank accounts.
  - [x] Sample investment decision note demonstrating thesis and pre-mortem workflow.
- [x] **Public Repository Readiness:**
  - [x] Clean template repository layout without private vault data.
  - [x] Comprehensive `README.md` with architecture, quickstart guide, and CLI commands.
  - [x] Open-source license (MIT).

---

## ⚡ Milestone: v0.5 Concurrent Asset Sync & Performance
- [ ] **Parallel Asset Enrichment & Pipeline Execution:**
  - [ ] Concurrent asset enrichment in `platforms/common.py` and `import_assets.py` using `ThreadPoolExecutor` or `asyncio`.
  - [ ] Parallelize external API & scraping queries across data providers (`yfinance`, `finnhub`, `justetf`, `ishares`, `vanguard`, `vaneck`).
  - [ ] Concurrent batch processing for ETF top holdings decomposition and cross-exposure sync (`sync_etf_holdings.py`).
  - [ ] Concurrent currency exchange rates fetching and portfolio valuation in `update_currencies.py`.
- [ ] **Automated Macroeconomic Synchronization (`sync_macro.py`):**
  - [ ] Automated fetcher for central bank rates, inflation, and bond yields (Yahoo Finance `^TNX`, `^IRX`, `GC=F`, `BZ=F` & NBP Web API for Polish rates/CPI).
  - [ ] Automatic frontmatter and indicator table updates in `10_Finance/Macro.md`.
  - [ ] CLI integration: `python run.py --macro` and inclusion in `python run.py --all`.
  - [ ] Macro risk indicators in Alert Rules Engine (e.g., `#alert/macro_inverted_yield_curve` and spread compression).
- [ ] **Rate Limiting, Throttling & Resilience:**
  - [ ] Configurable worker concurrency limits (pool size) in `config.yaml` / CLI flags.
  - [ ] Provider-specific throttling & polite pacing (avoid HTTP 429 Too Many Requests on Finnhub, Yahoo Finance, and JustETF).
  - [ ] Thread-safe retry policies with exponential backoff and jitter.
- [ ] **Thread-Safe Note Writing & Shared State:**
  - [ ] Atomic and thread-safe file writing for asset notes (`10_Finance/Assets/`) and ETF holdings (`10_Finance/ETF_Holdings/`).
  - [ ] Shared memory cache for FX rates, quotes, and metadata to eliminate redundant downloads across concurrent workers.
- [ ] **CLI UX & Performance Observability:**
  - [ ] Real-time concurrent progress indicators / status reporting (e.g. `rich` or `tqdm`) during imports and sync.
  - [ ] Pipeline execution timing metrics and speedup benchmarks in `run.py`.

---

## 🔮 Backlog & Future Enhancements

### 📊 Ideas, Watchlist & Macro Research
- [ ] Automatic Watchlist refresh & candidate generator via OpenBB / Finviz.
- [ ] Valuation catalyst notes explaining why scanners flagged specific tickers as undervalued.
- [x] `10_Finance/Macro.md` tracking central bank interest rates (Fed, ECB, NBP), CPI inflation, unemployment, and yield curves (10Y-2Y spread).
- [ ] FRED API integration (`fredapi`) for advanced macro data (M2 money supply, Fed balance sheet, initial jobless claims).
- [ ] Interactive Dataview / DataviewJS macro regime widget for `Overview.md` and `Welcome.md`.
- [ ] Investment reasoning & thesis documentation for all existing portfolio assets.

### 🔌 External Integrations
- [ ] Morningstar ratings & risk metrics via RapidAPI / OpenBB fallback.
- [ ] Technical analysis indicators via `tradingview-ta` (e.g., 200-day SMA trend alignment).
- [ ] News & RSS sentiment feeds (Seeking Alpha, MacroTrends).

### 🧹 Code Quality, Testing & Archival
- [ ] Automated unit test suite (`pytest`) for asset parsing, FX conversions, and alert evaluation.
- [ ] Portfolio history archival: retain daily entries for up to 2 years, archiving older records to `history-archive-YYYY.csv`.
- [ ] Ephemeral raw data rotation: automatically archive or prune raw CSV exports older than 1 year.
- [ ] Generic local currency instead of PLN.

---

## ✅ Completed Milestones

- [x] **v0.2 Alert Rules Engine & System Refactoring:**
  - [x] Refactor and organize `todo.md` roadmap.
  - [x] Implement modular Alert Rules Engine in `99_System/Scripts/alerts/`:
    - [x] `BaseAlertRule` interface and `AlertContext` loader.
    - [x] `OvervaluedRule` (`#alert/overvalued` - P/E threshold check).
    - [x] `DelistingRiskRule` (`#alert/delisting_risk` - ETF AUM minimum threshold).
    - [x] `InsiderSellingRule` (`#alert/insider_sell` - Finnhub SEC insider transactions).
    - [x] `AllocationDriftRule` (`#alert/allocation_drift` - single equity portfolio weight limit).
    - [x] `StopLossRule` (`#alert/stop_loss` - price breaching stop loss level).
  - [x] Centralize alert thresholds and toggles in `config.yaml`.
  - [x] Provide CLI runner `python 99_System/Scripts/alerts/engine.py` with standalone scanning and tagging.
  - [x] Update `Alerts.md` and dashboard views (`Overview.md`, portfolio views) to display the new alert categories.

- [x] **v0.1 Core Foundation:**
  - [x] Three-Portfolio Architecture implemented (*Safety Net*, *Long Term*, *Aggressive*) with strict capital silo principles.
  - [x] Multi-source asset enrichment (Yahoo Finance, JustETF, Finnhub).
  - [x] ETF top holdings decomposition and cross-exposure tracking (`sync_etf_holdings.py`).
  - [x] Portfolio performance timeline and Dataview dashboards.
