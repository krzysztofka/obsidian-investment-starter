# Investment Second Brain (GEMINI.md)

## 📌 Project Overview & Mission
This repository is an **Investment Second Brain & Portfolio Management System** powered by Obsidian markdown notes, Dataview dashboards, and automated Python scripts.

The vault is designed to maintain a single source of truth for:
1. **Live Portfolio Tracking:** Current holdings across multiple brokers (Degiro, Exante), unified in PLN with live FX rates and valuation metrics.
2. **Investment Ideas & Watchlists:** Tracking candidate assets, valuation scanners, and sector allocations.
3. **Decisions & Retrospectives:** Documenting the investment thesis, pre-mortems, execution details, and conducting periodic retrospective reviews to improve decision-making quality over time.
4. **Automated Intelligence:** Enriching asset notes with data from Yahoo Finance (`yfinance`), Finnhub (`finnhub-python`), and JustETF (`requests` + `beautifulsoup4`).

---

## 🌐 Language Standard
- **All vault content MUST be in English:** Markdown notes, dashboard views, chart labels, UI controls, frontmatter fields, templates, scripts, code comments, and documentation must always be written in **English** (portfolio currency remains PLN).

---

## 🏛️ Three-Portfolio Architecture & Strict Capital Silo Rule

The vault enforces a **three-bucket framework** with complete independence between sub-portfolios:

1. **🛡️ Safety Net Portfolio (`Safety_portfolio.md`):**
   - **Mandate:** Emergency liquidity reserves, currency cushions, and guaranteed inflation protection.
   - **Key Assets:** Bank cash (EUR, PLN), Polish inflation-indexed retail treasury bonds (ROD, EDO). *(Uninvested broker cash is treated as unallocated dry powder with portfolio: null)*.
   - **Objective:** Capital preservation with zero market risk.

2. **🏛️ Long Term Portfolio (`Long_term_portfolio.md`):**
   - **Mandate:** Multi-decade wealth building, retirement foundation, and generational purchasing power preservation.
   - **Key Assets:** Physical real estate, physical allocated gold, tax-advantaged accounts (IKE), core multi-asset index ETFs (e.g., Vanguard LifeStrategy), broad dividend leaders, sovereign bond ETFs.
   - **Objective:** Steady compound total return with controlled drawdowns and autonomous internal rebalancing.

3. **🚀 Aggressive Portfolio (`Aggressive_portfolio.md`):**
   - **Mandate:** Alpha generation, high-conviction stock picking, and cyclical / thematic sector opportunities.
   - **Key Assets:** Direct individual equities (US growth/tech, GPW cyclical leaders), concentrated/thematic ETFs (defense, healthcare, emerging markets).
   - **Objective:** Maximum capital appreciation accepting higher single-stock volatility.

### ⚖️ Portfolio Silo Principle & Disciplined Exceptions

- **General Principle (Autonomous Silos by Default):**
  - As a general rule, each portfolio operates as an **independent, self-contained silo**.
  - Daily trades, position sizing, and routine rebalancing should remain strictly within the assigned portfolio to prevent risk creep, undisciplined bleeding of funds, or using low-risk assets to casually rationalize reckless speculation.
  - Assets in `Safety Net` exist for capital security and should not be casually treated as the fixed-income cushion to justify excess equity risk in `Long Term` or `Aggressive`.

- **Permissible Exceptions in Exceptional Situations:**
  Cross-portfolio capital transfers are fully permitted under well-defined, conscious strategic conditions:
  1. **Strategic De-risking (Profit Harvesting):** Moving realized gains from outperforming positions in `Aggressive` (e.g., trimming high-cyclical multi-baggers like KGHM) into `Long Term` core index ETFs (e.g., Vanguard LifeStrategy) or hard assets to permanently lock in wealth.
  2. **Replenishing the Safety Cushion:** Injecting capital into `Safety Net` to restore emergency reserves following major life events or unplanned liquidity needs.
  3. **Generational Market Dislocations:** Mobilizing surplus dry powder to capitalize on rare, once-in-a-decade market crashes, provided the core safety net buffer remains intact.

- **Documentation Protocol for Exceptions:**
  - Cross-portfolio transfers must **never be done on emotional impulse**.
  - Every exception must be explicitly documented in a formal decision note in `20_Decisions/`, specifying the source portfolio, destination portfolio, amount, and strategic rationale.

---

## 📂 Vault Directory Structure

```text
trader/
├── 00_Raw/                         # Raw broker data exports (gitignored / ephemeral)
│   ├── archive/                    # Rotated raw broker exports (> 1 year)
│   ├── pko_bp_bonds/               # PKO BP retail bonds Excel files (StanRachunkuRejestrowego_*.xls)
│   ├── mbank_ike/                  # mBank eMakler IKE CSV files (*.csv)
│   ├── mbank_ikze/                 # mBank eMakler IKZE CSV files (*.csv)
│   ├── degiro/                     # Degiro CSV export files (*.csv)
│   └── exante/                     # Exante CSV export files (*.csv)
├── 10_Finance/                     # Core financial tracking
│   ├── Assets/                     # 1 Markdown note per asset/cash holding
│   ├── ETF_Holdings/               # Underlying company notes tracked inside portfolio ETFs
│   ├── History/                    # Historical snapshots (e.g., portfolio.csv)
│   │   └── archive/                # Partitioned yearly archives (history-archive-YYYY.csv)
│   ├── Watchlist/                  # Watchlists and candidate assets
│   └── Macro.md                    # Macroeconomic indicators, central bank rates & regime tracking
├── 20_Decisions/                   # Investment decisions, trade logs, and retrospectives
│   └── 2026/                       # Decisions grouped by year / status
├── 99_System/                      # System tools, templates & configurations
│   ├── Scripts/                    # Python automation suite
│   │   ├── history/                # History update & sync utilities
│   │   ├── integrations/           # API integrations (yfinance, JustETF, Finnhub, NBP, Eurostat, Stooq)
│   │   ├── model/                  # Data models corresponding to vault templates (e.g., Asset)
│   │   ├── platforms/              # Broker platform import modules (Degiro, Exante, mBM, pkobp, common)
│   │   ├── sync_etf_holdings.py    # ETF top holdings synchronization engine
│   │   ├── sync_macro.py           # Macroeconomic dashboard synchronization engine
│   │   └── import_instructions.md  # Detailed manual import documentation
│   ├── Templates/                  # Vault templates (asset, decision, retrospective, watchlist, macro)
│   │   ├── asset_template.md       # Base template for assets
│   │   ├── etf_holding_template.md # Template for ETF underlying holdings
│   │   ├── macro_template.md       # Template for macroeconomic dashboard (Macro.md)
│   │   ├── decision_template.md    # Template for investment decisions
│   │   ├── retrospective_template.md # Template for decision reviews
│   │   └── watchlist_item_template.md # Template for watchlist items
│   └── Views/                      # Reusable DataviewJS custom views (e.g., alert_banner, open_decisions, stooq_chart)
├── Alerts.md                       # Active alerts dashboard (Dataview)
├── Portfolio_performance.md        # Historical performance & valuation charts (DataviewJS + Charts)
├── Overview.md                     # Portfolio valuation, sector breakdown chart & table
├── Safety_portfolio.md             # Safety net portfolio breakdown (cash cushions & capital preservation)
├── Long_term_portfolio.md          # Long term portfolio breakdown (broad ETFs, bonds, real estate, gold)
├── Aggressive_portfolio.md         # Aggressive portfolio breakdown (growth equities & thematic ETFs)
├── Welcome.md                      # Navigation hub & system overview
├── pyproject.toml                  # Python project metadata & dependency manifest
├── config.yaml                     # Root reference config
└── GEMINI.md                       # AI assistant context & system guidelines
```

---

## 🏷️ Vault Note Templates & Schemas

Note frontmatter schemas and body layouts are defined dynamically in the system templates:
- **Asset Template:** [`99_System/Templates/asset_template.md`](99_System/Templates/asset_template.md)
- **ETF Holding Template:** [`99_System/Templates/etf_holding_template.md`](99_System/Templates/etf_holding_template.md)
- **Macro Dashboard Template:** [`99_System/Templates/macro_template.md`](99_System/Templates/macro_template.md)
- **Decision Template:** [`99_System/Templates/decision_template.md`](99_System/Templates/decision_template.md)
- **Retrospective Template:** [`99_System/Templates/retrospective_template.md`](99_System/Templates/retrospective_template.md)
- **Watchlist Item Template:** [`99_System/Templates/watchlist_item_template.md`](99_System/Templates/watchlist_item_template.md)

Refer to the respective template file for the latest schema, frontmatter fields, and note structure. Never hardcode Markdown note templates directly inside Python source code; always maintain templates in `99_System/Templates/` and render them dynamically.


---

## ⚡ Automation Workflows & Commands

All scripts are executed with Python 3.x using the virtual environment / installed dependencies:

```bash
# 1. Install dependencies
pip install .

# 🚀 UNIFIED RUNNER (run.py): Execute all or specific pipeline actions
python run.py --all                               # Run full pipeline: import -> rates -> macro -> etfs -> alerts -> history
python run.py --import                            # Import broker exports (enabled platforms or use --platform / --file)
python run.py --list-platforms                    # List available platform extensions and their enabled status
python run.py --enable-platform <id>              # Enable a platform extension in config.yaml
python run.py --disable-platform <id>             # Disable a platform extension in config.yaml
python run.py --import --platform pko_bp_bonds    # Import PKO BP treasury retail bonds
python run.py --import --platform mbank_ike       # Import mBank IKE positions
python run.py --import --platform mbank_ikze      # Import mBank IKZE positions
python run.py --import --platform degiro          # Import Degiro positions
python run.py --import --platform exante          # Import Exante positions (CSV or API)
python run.py --import --api                      # Import live positions directly via Exante REST API
python run.py --update-rates                      # Refresh live FX rates and update value_pln
python run.py --macro                             # Synchronize macroeconomic dashboard indicators, yields & rates
python run.py --sync-etfs                         # Synchronize ETF top holdings, overlap & exposures
python run.py --alerts                            # Scan and evaluate portfolio alerts (Alert Rules Engine)
python run.py --history                           # Synchronize historical snapshots to portfolio.csv
python run.py --archive                           # Archive historical portfolio records (>2yr) and rotate raw exports (>1yr)
python run.py --archive --dry-run                 # Preview archival and rotation without file changes
python run.py --update-rates --alerts             # Chain multiple actions together

# --- Or run individual modules directly ---
# 2. Import broker exports (enabled platforms or specific platform/file/API)
python 99_System/Scripts/import_assets.py
# (Or: python 99_System/Scripts/platforms/pko_bp_bonds.py)
# (Or: python 99_System/Scripts/platforms/mbank_ike.py)
# (Or: python 99_System/Scripts/platforms/mbank_ikze.py)
# (Or: python 99_System/Scripts/platforms/degiro.py)
# (Or: python 99_System/Scripts/platforms/exante.py --api)
# (Or: python 99_System/Scripts/import_assets.py --file 00_Raw/pko_bp_bonds/sample_pkobp.xls)
# (Or: python 99_System/Scripts/import_assets.py --file 00_Raw/mbank_ikze/sample_ikze.csv)


# 3. Synchronize macroeconomic indicators & yield curves
python 99_System/Scripts/sync_macro.py
# (Or dry-run: python 99_System/Scripts/sync_macro.py --dry-run)

# 4. Refresh live currency rates and update value_pln
python 99_System/Scripts/update_currencies.py

# 5. Scan & evaluate portfolio risk and valuation alerts via Alert Rules Engine
python 99_System/Scripts/alerts/engine.py
# (Or dry-run: python 99_System/Scripts/alerts/engine.py --dry-run)
# (Or single rule: python 99_System/Scripts/alerts/engine.py --rule overvalued)

# 6. Synchronize portfolio historical timeline
python 99_System/Scripts/history/update_portfolio.py

# 7. Execute data retention, history archival and raw export rotation
python 99_System/Scripts/history/retention.py
# (Or dry-run: python 99_System/Scripts/history/retention.py --dry-run)

# 8. Discover watchlist candidates & generate notes with OpenBB / Morningstar
python 99_System/Scripts/discover_watchlist.py --strategy quality_growth
python 99_System/Scripts/discover_watchlist.py --add NVDA

# 9. Synchronize ETF top holdings, overlap and cross-exposure notes
python 99_System/Scripts/sync_etf_holdings.py
# (Or: python 99_System/Scripts/sync_etf_holdings.py --limit 15)

# 10. Run automated unit test suite (pytest)
python -m pytest

# 11. Linting, code formatting, and static type checking
python -m ruff check .                           # Run linter checks
python -m ruff format --check .                  # Check formatting style
python -m ruff format .                          # Auto-format codebase
python -m mypy 99_System/Scripts                 # Static type checking
```

---

## 🧠 Decision & Retrospective Process

To avoid emotional trading and maintain a disciplined process, every major buy/sell decision follows a structured lifecycle in `20_Decisions/`:

1. **Decision Thesis Note (`20_Decisions/YYYY-MM-DD_<ticker>_<BUY|SELL>.md`):**
   - Created from [`99_System/Templates/decision_template.md`](99_System/Templates/decision_template.md).
   - **Context:** Why this asset? Which watchlist / scanner identified it?
   - **Thesis:** Fundamental catalyst, expected holding period, target valuation / exit price.
   - **Pre-Mortem:** If this trade fails, what is the most likely cause?
   - **Risk Management:** Stop loss, max portfolio allocation % limit.
2. **Execution Log:**
   - Date, execution price, platform/broker, fees, quantity.
3. **Quarterly / Annual Retrospective (`20_Decisions/YYYY-QN_Retrospective.md`):**
   - Created from [`99_System/Templates/retrospective_template.md`](99_System/Templates/retrospective_template.md).
   - Review closed trades and long-standing positions.
   - Did reality match the original thesis?
   - Was success/failure due to skill, luck, or macro factors?
   - Actionable takeaways for future trades.

---

## 🔍 Ideas & Watchlist Pipeline

Located in `10_Finance/Watchlist/`:
- **Ideas:** Unscreened opportunities, articles, analyst notes, and sector trends.
- **Watchlists (`10_Finance/Watchlist/Watchlist.md`):** Dynamic Dataview dashboard and structured tables displaying target entry prices, valuation indicators, analyst consensus, and broker platforms.
- **Candidate Generator (`99_System/Scripts/discover_watchlist.py`):** Automated scanner generating notes from [`99_System/Templates/watchlist_item_template.md`](99_System/Templates/watchlist_item_template.md).
- **Sector Allocation Checks:** Checking how potential new buys impact portfolio sector diversification according to `config.yaml`.

---

## 🔑 Integrations & Environment Variables

Create `.env` at the root directory:
```env
FINNHUB_API_KEY=your_api_key_here
EXANTE_API_KEY=your_exante_api_key_or_app_id
EXANTE_API_SECRET=your_exante_api_secret_or_shared_key
EXANTE_ACCOUNT_ID=your_account_id_here
EXANTE_API_URL=https://api-live.exante.eu
```
- **Exante REST API Integration (`requests`):** Live account synchronization of cash balances (multi-currency) and open positions directly into `10_Finance/Assets/` without manual CSV exports (`python run.py --import --api` or `python 99_System/Scripts/platforms/exante.py --api`).
- **Finnhub Integration:** Analyst recommendation consensus ratings and SEC insider trading alerts.
- **Yahoo Finance (`yfinance`):** Quotes, P/E ratios, dividend yields, market caps, FX rates.
- **JustETF (`requests` + `beautifulsoup4`):** ISIN-based ETF metadata, TER, replication type, domicile, and sector breakdowns.
- **iShares Integration (`requests`):** Automatic resolution of official BlackRock / iShares product websites (US & Europe) and fund metadata.
- **Vanguard Integration (`requests`):** Automatic resolution of official Vanguard product websites (US Investor & UK/Europe UCITS) and fund profiles.
- **VanEck Integration (`requests`):** Automatic resolution of official VanEck product websites (Europe UCITS & US) and fund metadata.
- **Stooq Integration (`stooq`):** Automatic resolution of standardized Stooq market symbols (`stooq_ticker`) for equities, UCITS/US ETFs, retail treasury bonds / 10Y benchmarks (`10ply.b`), precious metals (`xauusd`), and interactive HTML5 technical charts (`stooq_chart.js`).
- **NBP Integration (`api.nbp.pl` & `static.nbp.pl`):** Official Polish exchange rates (Table A fixing), domestic gold fixings, and central bank base interest rates (`NBPMacroSupplier`).
- **Eurostat Integration (`ec.europa.eu/eurostat`):** Polish 10Y sovereign yields (Maastricht criterion), European & Polish HICP inflation, and labor indicators (`EurostatMacroSupplier`).
- **OpenBB & Morningstar (`openbb` / `yfinance` fallback):** Morningstar ratings, Morningstar risk metrics, valuation overviews, and automated watchlist candidate screening.

