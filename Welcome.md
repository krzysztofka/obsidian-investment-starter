# 🧠 Welcome to Investment Second Brain

Welcome to your **Investment Second Brain & Portfolio Management System** — a unified, Obsidian-powered command center designed to track holdings across multiple brokers, automate market intelligence, and enforce disciplined investment decisions.

> 📖 **System Documentation & Guidelines:** Read [[GEMINI|GEMINI.md]] for the complete system architecture, automation workflows, directory structure, and API integrations.

---

## 🧭 Navigation & Core Dashboards

| Dashboard | Description | Link |
| :--- | :--- | :--- |
| 📊 **Portfolio Overview** | Live portfolio valuation in PLN, consolidated asset class & sector allocation charts, and merged holdings. | [[Overview]] |
| 🛡️ **Safety Net Portfolio** | Emergency fund, cash cushions, and capital preservation holdings. | [[Safety_portfolio\|Safety Net]] |
| 🏛️ **Long Term Portfolio** | Broad-market index ETFs, sovereign bond ETFs, real estate, and physical gold. | [[Long_term_portfolio\|Long Term]] |
| 🚀 **Aggressive Portfolio** | High-growth stock picks, thematic ETFs, and concentrated sector investments. | [[Aggressive_portfolio\|Aggressive]] |
| 📈 **Historical Performance** | Valuation history timeline, cumulative equity performance, and portfolio milestone charts. | [[Portfolio_performance\|Historical Performance]] |
| 🚨 **Active Alerts** | Valuation warnings (`#alert/overvalued`), delisting risks, and SEC insider trading signals (`#alert/insider_sell`). | [[Alerts]] |
| 🔍 **Watchlist & Candidates** | Opportunity pipeline, valuation scanner candidates, target entry prices, and analyst consensus ratings. | [[10_Finance/Watchlist/Watchlist\|Watchlist]] |
| 🌐 **Macro Dashboard** | Global & domestic macroeconomic indicators, central bank policy rates, CPI, and yield curve spreads. | [[10_Finance/Macro\|Macro Dashboard]] |
| 📝 **Roadmap & Improvements** | Planned features, integration ideas, backlog, and system improvement items. | [[todo\|Things to Improve (TODO)]] |

---

## ⚡ Core Capabilities

- **Unified Multi-Broker Tracking:** Consolidates Degiro, Exante (live REST API or CSV exports), and cash cushions converted into **PLN** with live FX rates.
- **Automated Intelligence:** Enriches asset notes with live quotes, P/E ratios, dividend yields, ETF structures, and Morningstar metrics via Yahoo Finance, Finnhub, and JustETF.
- **Structured Decisions & Retrospectives:** Formulates pre-mortems, investment theses, and quarterly retrospectives in `20_Decisions/` to continuously improve investment discipline.
- **Automated Data Imports:** Import broker positions seamlessly via live Exante REST API and Degiro CSV exports using `python run.py --import` or the interactive runner below.

---

## 🚀 Interactive Pipeline Action Center

Click any button below to execute the pipeline directly within Obsidian (or copy command to clipboard in non-desktop / restricted environments):

```dataviewjs
await dv.view("99_System/Views/runner_widget");
```

---

## 📥 Broker Import & Synchronization

Follow this guide to synchronize holdings from **Degiro** and **Exante**:

### 1. Import Modes & Configuration

The vault supports both **live REST API synchronization** and **raw CSV exports**. Default import modes are configured in [[99_System/config.yaml]]:

```yaml
# 99_System/config.yaml
import:
  exante:
    default_mode: "api"  # Options: 'api' (live Exante REST API) or 'csv' (00_Raw/Exante)
  degiro:
    default_mode: "csv"  # Options: 'csv' (00_Raw/Degiro)
```

#### A. Exante Live REST API Synchronization (Default)
When `default_mode: "api"` is set (or `--api` flag is used), positions and multi-currency cash balances are pulled directly from Exante's servers without downloading CSV files.
- Configure credentials in `.env`:
  ```env
  EXANTE_API_KEY=your_application_id_here
  EXANTE_API_SECRET=your_shared_key_here
  EXANTE_ACCOUNT_ID=your_account_id (optional)
  ```

#### B. Raw CSV Exports (Degiro & Exante Fallback)
- **Degiro:** Place CSV exports into `00_Raw/Degiro/` *(pattern: `portfolio-YYYY-MM-DD.csv`)*
- **Exante (CSV mode):** Place CSV exports into `00_Raw/Exante/` *(pattern: `Account_YYYY-MM-DD_*.csv`)*

> [!TIP]
> When importing from CSV, the import script automatically selects the most recent file based on timestamp and filename dates, or you can specify a file directly with `--file`.

---

### 2. Execute the Import

Choose whichever execution method fits your environment:

#### Method A: Direct Execution via Interactive Action Center
Click the **📥 Import Degiro & Exante (`--import`)** or **🚀 Run Full Pipeline (`--all`)** button in the Action Center above. The execution output and progress will stream live in the console box.

> [!NOTE]
> The full pipeline (`--all`) enriches all holdings with live data from Yahoo Finance, JustETF, and Finnhub, which takes approximately 2 to 3 minutes. The Action Center uses unbuffered streaming and mirrors all output to `99_System/runner.log`, automatically preserving your console view even when vault files trigger background Dataview re-renders.

#### Method B: Command Line Terminal
Open your terminal in the workspace root and run:
```bash
# 1. Run standard import (uses default_mode from config.yaml -> Degiro CSV + Exante API):
python run.py --import

# 2. Run full pipeline (import -> FX rates -> macro -> ETF overlap -> alerts -> history):
python run.py --all

# 3. Explicitly force Exante API or CSV mode:
python run.py --import --api      # Force Exante API mode
python run.py --import --csv      # Force Exante CSV mode

# 4. Import a single platform:
python run.py --import --platform degiro
python run.py --import --platform exante
```

---

### 3. What Happens After Import?

1. **Frontmatter & Valuation Sync:** Asset notes in `10_Finance/Assets/*.md` are updated with the latest position sizes, purchase prices, and converted `value_pln`.
2. **Safe Platform Pruning:** Positions imported from Degiro/Exante have `source: platform`. Closed/sold positions are pruned automatically. Manual assets (physical gold, real estate, retail bonds) use `source: manual` and are **never** removed.
3. **Intelligence Enrichment:** Metadata, P/E, dividend yields, and sector classifications are enriched from Yahoo Finance, JustETF, and Finnhub.
4. **History Timeline Update:** `10_Finance/History/portfolio.csv` is automatically updated and deduplicated for performance charts.

For in-depth technical details, refer to [[99_System/Scripts/import_instructions|Detailed Import Documentation]] and [[GEMINI|GEMINI.md]].

---

## 🛠️ Backlog & Improvements
Check out [[todo|todo.md]] for the active backlog and future ideas to improve the vault (e.g. macro indicators, new broker integrations, API enhancements, and test coverage).