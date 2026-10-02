# 🧠 Obsidian Investment Brain

A unified **Investment Second Brain & Portfolio Management System** built with **Obsidian**, **Dataview**, and an automated **Python intelligence pipeline**.

Consolidates holdings across multiple brokers (Degiro, Exante REST API / CSV, mBM IKE/IKZE) unified in **PLN** with live FX rates, automated macroeconomic intelligence, ETF look-through exposure analytics, and structured investment decision retrospectives.

---

## 🏛️ Core Architecture & Three-Portfolio Framework

The system enforces an autonomous **three-bucket capital allocation framework**:

| Sub-Portfolio | Mandate | Primary Assets | Target Objective |
| :--- | :--- | :--- | :--- |
| 🛡️ **[Safety Net](Safety_portfolio.md)** | Emergency liquidity reserves & inflation protection | Bank cash (PLN, EUR), Polish retail inflation-indexed treasury bonds (EDO, ROD) | Capital preservation & zero market risk |
| 🏛️ **[Long Term](Long_term_portfolio.md)** | Generational wealth building & retirement foundation | Tax-advantaged accounts (IKE/IKZE), core broad index ETFs, sovereign bonds, physical gold, real estate | Steady compounding with controlled drawdowns |
| 🚀 **[Aggressive](Aggressive_portfolio.md)** | Alpha generation & sector rotation | Growth tech equities, cyclical leaders (GPW/US), concentrated thematic ETFs | Maximum capital appreciation accepting volatility |

---

## ✨ Key Capabilities

- 📊 **Multi-Broker Portfolio Tracking:** Consolidates Degiro, Exante (live REST API & CSV), and mBank Brokerage (mBM IKE & IKZE) into single markdown note representations per asset in `10_Finance/Assets/`.
- 💱 **Live FX & Currency Normalization:** Automatically tracks currency exchange rates (USD/PLN, EUR/PLN, GBP/PLN, CHF/PLN) and calculates unified portfolio valuations in PLN.
- 🌐 **Macroeconomic Dashboard:** Synchronizes central bank policy rates (FED, ECB, NBP), inflation CPI, and 10Y/2Y sovereign bond yield curves via [sync_macro.py](99_System/Scripts/sync_macro.py).
- 🔍 **ETF Look-Through & Exposure Engine:** Deconstructs portfolio ETFs into underlying company holdings in `10_Finance/ETF_Holdings/`, computing aggregate overlap and single-stock cross-exposures.
- 🚨 **Automated Alert Rules Engine:** Scans holdings for valuation anomalies, dividend suspensions, delisting risks, and SEC insider trading transactions.
- 📝 **Investment Decision Lifecycle & Pre-Mortems:** Standardized investment thesis creation (`20_Decisions/YYYY-MM-DD_<ticker>_<BUY|SELL>.md`) and quarterly retrospectives (`20_Decisions/YYYY-QN_Retrospective.md`) to build trading discipline.
- ⚡ **Interactive Obsidian Action Center:** One-click script execution directly inside Obsidian using DataviewJS with live console output streaming.

---

## 📂 Vault Structure

```text
├── 00_Raw/                         # Raw broker data exports (gitignored / ephemeral)
│   ├── Degiro/                     # Degiro CSV exports
│   ├── Exante/                     # Exante CSV exports
│   └── mBM/                        # mBM CSV exports (ike-*.csv, ikze-*.csv)
├── 10_Finance/                     # Core financial tracking
│   ├── Assets/                     # 1 Markdown note per asset / cash holding
│   ├── ETF_Holdings/               # Underlying company notes tracked inside ETFs
│   ├── History/                    # Historical snapshots (portfolio.csv)
│   ├── Watchlist/                  # Watchlists, screener candidate assets & thesis
│   └── Macro.md                    # Macroeconomic indicators & central bank rates
├── 20_Decisions/                   # Investment decisions, trade logs, and retrospectives
│   └── 2026/                       # Decisions grouped by year / status
├── 99_System/                      # Automation suite, templates & configurations
│   ├── Scripts/                    # Python automation suite
│   │   ├── alerts/                 # Portfolio alert rules engine
│   │   ├── history/                # History update & sync utilities
│   │   ├── integrations/           # Market data APIs (yfinance, JustETF, Finnhub, Stooq)
│   │   ├── model/                  # Asset & holding data models
│   │   ├── platforms/              # Broker platform import modules (Degiro, Exante, mBM)
│   │   ├── sync_etf_holdings.py    # ETF top holdings synchronization engine
│   │   └── sync_macro.py           # Macroeconomic data synchronization
│   ├── Templates/                  # Note templates (assets, decisions, watchlists)
│   ├── Views/                      # Reusable DataviewJS UI views & widgets
│   └── config.yaml                 # System configurations & sector mapping
├── Alerts.md                       # Active risk & valuation alerts dashboard
├── Overview.md                     # Portfolio valuation & sector breakdown
├── Portfolio_performance.md        # Historical valuation & equity performance charts
├── Safety_portfolio.md             # Safety net portfolio breakdown
├── Long_term_portfolio.md          # Long term portfolio breakdown
├── Aggressive_portfolio.md         # Aggressive portfolio breakdown
├── Welcome.md                      # Obsidian interactive landing page & action center
├── run.py                          # Unified CLI pipeline runner
└── config.yaml                     # Root reference configuration
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites

- **Python 3.10+**
- **Obsidian** with the following community plugins enabled:
  - **[Dataview](https://github.com/blacksmithgu/obsidian-dataview)** *(Required: Enable JavaScript Queries in settings)*
  - **[Obsidian Charts](https://github.com/phibr0/obsidian-charts)** *(Required for allocation & performance charts)*

### 2. Environment Setup

Clone the repository and install Python dependencies:

```bash
git clone https://github.com/krzysztofka/obsidian-investment-brain.git
cd obsidian-investment-brain

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install .
```

### 3. API Keys Configuration (Optional)

Create a `.env` file in the root directory to enable live API feeds:

```env
# Finnhub API (for analyst ratings & insider transactions)
FINNHUB_API_KEY=your_finnhub_api_key

# Exante REST API (for live position & cash synchronization)
EXANTE_API_KEY=your_application_id
EXANTE_API_SECRET=your_shared_key
EXANTE_ACCOUNT_ID=your_account_id
EXANTE_API_URL=https://api-live.exante.eu
```

---

## ⚡ Automation CLI Commands

All automation tasks can be run via the unified CLI runner [run.py](run.py):

```bash
# 🚀 Run complete pipeline (import -> FX rates -> macro -> ETF sync -> alerts -> history)
python run.py --all

# 📥 Import broker holdings
python run.py --import                   # Import Degiro CSV & Exante API / CSV
python run.py --import --platform mbm    # Import mBM IKE & IKZE accounts
python run.py --import --platform ike    # Import mBM IKE positions only
python run.py --import --platform ikze   # Import mBM IKZE positions only
python run.py --import --api             # Force Exante live REST API mode
python run.py --import --csv             # Force Exante raw CSV mode

# 💱 Update FX exchange rates and asset valuations (PLN)
python run.py --update-rates

# 🌐 Synchronize macroeconomic indicators & central bank rates
python run.py --macro

# 🔍 Synchronize ETF look-through top holdings & overlap
python run.py --sync-etfs

# 🚨 Scan portfolio for valuation & insider trading alerts
python run.py --alerts

# 📈 Update portfolio timeline snapshots for historical charts
python run.py --history
```

---

## 🔒 Security & Privacy

- Sensitive files such as `.env`, raw broker CSV statements (`00_Raw/*`), and cache files are strictly included in [.gitignore](.gitignore) to prevent accidental credential or personal financial data exposure.
- All broker imports operate locally or through official authenticated REST APIs directly on your machine.

---

## 📄 License

This repository is maintained for private personal portfolio management and financial intelligence.
