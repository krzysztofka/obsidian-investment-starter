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

- 📊 **Multi-Broker Portfolio Tracking:** Consolidates Degiro, Exante (live REST API & CSV), mBank Brokerage (mBM IKE & IKZE), and PKO BP retail bonds into single markdown note representations per asset in `10_Finance/Assets/`.
- 💱 **Live FX & Currency Normalization:** Automatically tracks currency exchange rates (USD/PLN, EUR/PLN, GBP/PLN, CHF/PLN) and calculates unified portfolio valuations in PLN.
- 🎯 **Model Portfolios & Rebalance Corridors:** Defines target allocations per portfolio silo (by asset class, dominant sector, or specific key assets) with tolerance corridors ($\pm 5\%$) and minimum trade thresholds to eliminate micro-transactions.
- 🌐 **Macroeconomic Dashboard:** Synchronizes central bank policy rates (FED, ECB, NBP), inflation CPI, and 10Y/2Y sovereign bond yield curves via [sync_macro.py](99_System/Scripts/sync_macro.py).
- 🔍 **ETF Look-Through & Exposure Engine:** Deconstructs portfolio ETFs into underlying company holdings in `10_Finance/ETF_Holdings/`, computing aggregate overlap and single-stock cross-exposures.
- 🚨 **Automated Alert Rules Engine:** Scans holdings for valuation anomalies, dividend suspensions, delisting risks, and SEC insider trading transactions.
- 🩺 **System Sanity & External Health Probes:** Automated health probes for external market APIs (`python run.py --health`) and frontmatter/data integrity verification (`python run.py --sanity`).
- 📝 **Investment Decision Lifecycle & Pre-Mortems:** Standardized investment thesis creation (`20_Decisions/YYYY-MM-DD_<ticker>_<BUY|SELL>.md`) and quarterly retrospectives (`20_Decisions/YYYY-QN_Retrospective.md`) to build trading discipline.
- ⚡ **Interactive Obsidian Action Center:** One-click script execution directly inside Obsidian using DataviewJS with live console output streaming.

---

## 📂 Vault Structure

```text
├── 00_Raw/                         # Raw broker data exports (gitignored / ephemeral)
│   ├── archive/                    # Rotated raw broker exports (> 1 year)
│   ├── degiro/                     # Degiro CSV export files (*.csv)
│   ├── exante/                     # Exante CSV export files (*.csv)
│   ├── mbank_ike/                  # mBank eMakler IKE CSV files (*.csv)
│   ├── mbank_ikze/                 # mBank eMakler IKZE CSV files (*.csv)
│   └── pko_bp_bonds/               # PKO BP retail bonds Excel files (StanRachunkuRejestrowego_*.xls)
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
│   │   ├── platforms/              # Broker platform import modules (Degiro, Exante, mBank, PKO BP)
│   │   ├── health_check.py         # External integrations health check & diagnostics
│   │   ├── sanity_check.py         # Vault frontmatter & data integrity diagnostics
│   │   ├── sync_etf_holdings.py    # ETF top holdings synchronization engine
│   │   └── sync_macro.py           # Macroeconomic data synchronization
│   ├── Templates/                  # Note templates (assets, decisions, watchlists)
│   └── Views/                      # Reusable DataviewJS UI views & widgets
├── .vault_version                  # Vault schema & migration version marker (e.g. 0.8.0)
├── Alerts.md                       # Active risk & valuation alerts dashboard
├── Health.md                       # Integrations health & connectivity diagnostics dashboard
├── Overview.md                     # Portfolio valuation & sector breakdown
├── Portfolio_performance.md        # Historical valuation & equity performance charts
├── Safety_portfolio.md             # Safety net portfolio breakdown
├── Long_term_portfolio.md          # Long term portfolio breakdown
├── Aggressive_portfolio.md         # Aggressive portfolio breakdown
├── Welcome.md                      # Obsidian interactive landing page & action center
├── run.py                          # Unified CLI pipeline runner
├── patch.py                        # Vault sequential patch migration engine
└── config.yaml                     # Root reference configuration
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites

- **Python 3.10+**
- **Obsidian**:
  - The repository comes pre-bundled with required plugins in `.obsidian/plugins/` (**[Dataview](https://github.com/blacksmithgu/obsidian-dataview)** and **[Obsidian Charts](https://github.com/phibr0/obsidian-charts)**).
  - When opening the vault in Obsidian for the first time, click **"Trust author and enable plugins"** and ensure **"Enable JavaScript Queries"** is toggled ON under Dataview settings.

### 2. Environment Setup

Clone the repository and install Python dependencies:

```bash
git clone https://github.com/krzysztofka/obsidian-investment-starter.git
cd obsidian-investment-starter

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install .
```

### 3. Initialize Your Vault

Run the interactive setup wizard via [init.py](init.py) (or `python run.py --init`):

```bash
# Interactive setup (platforms, base currency, investor profile, and clean/demo mode)
python init.py

# Or via unified runner:
python run.py --init
```

The wizard guides you through:
1. **Initial Data Mode:**
   - **Clean Vault (Default):** Purges sample demo assets, mock raw files, and dummy history, leaving you with a pristine vault ready for your real holdings.
   - **Demo Vault:** Preserves synthetic demonstration assets across all three portfolios and mock history for exploring dashboards.
2. **Platform Extensions:** Select which broker extensions to enable (`pko_bp_bonds`, `mbank_ike`, `mbank_ikze`, `degiro`, `exante`).
3. **Base Currency & Localization:** Select your primary portfolio currency (`PLN`, `EUR`, `USD`, `GBP`, `CHF`, or custom ISO-4217).
4. **Investor Profile & Rebalancing Rules:** Configure risk tolerance (Conservative, Moderate, Aggressive), Belka tax DCA sensitivity, and single-stock allocation cap.
5. **Environment Configuration:** Automatically copies `.env.example` -> `.env`.
6. **Diagnostics:** Verifies installed dependencies and optionally tests market API connectivity.

> [!TIP]
> **Non-Interactive & Advanced CLI Flags:**
> - `python init.py --clean` / `python run.py --init --clean`: Non-interactively initialize as a Clean Vault.
> - `python init.py --demo` / `python run.py --init --demo`: Non-interactively initialize as a Demo Vault.
> - `python init.py --target ../my-vault`: Scaffold a complete downstream personal vault into an external directory.

### 4. Open in Obsidian

1. Open **Obsidian**, choose **"Open folder as vault"**, and select the repository directory.
2. In Obsidian Settings → **Community plugins**, confirm plugins are enabled.
3. In Obsidian Settings → **Dataview**, confirm **"Enable JavaScript Queries"** is enabled.
4. Open **[Welcome.md](Welcome.md)** or **[Overview.md](Overview.md)** to access your command center.

### 5. API Keys Configuration & Pipeline Execution (Optional)

Configure your API credentials in `.env` (if using Finnhub or Exante REST API):

```env
# Finnhub API (for analyst ratings & insider transactions)
FINNHUB_API_KEY=your_finnhub_api_key

# Exante REST API (for live position & cash synchronization)
EXANTE_API_KEY=your_application_id
EXANTE_API_SECRET=your_shared_key
EXANTE_ACCOUNT_ID=your_account_id
EXANTE_API_URL=https://api-live.exante.eu
```

Execute your initial portfolio pipeline:

```bash
# 🚀 Run complete pipeline (import -> FX rates -> macro -> ETF sync -> alerts -> history)
python run.py --all
```

---

## ⚡ Automation CLI Commands

All automation tasks can be run via the unified CLI runner [run.py](run.py):

```bash
# 🚀 Run complete pipeline (import -> FX rates -> macro -> ETF sync -> alerts -> history)
python run.py --all

# ⚙️ Initialize / re-configure vault
python run.py --init                    # Interactive setup (currency, profile, platforms, data mode)
python run.py --init --clean            # Initialize as Clean Vault (wipe sample assets & dummy history)

# 🩺 Diagnostics & Vault Sanity
python run.py --health                   # Run external integrations connectivity diagnostics
python run.py --sanity                   # Verify note frontmatters & history timeline integrity
python run.py --sanity --fix             # Auto-repair portfolio.csv chronological monotonicity

# 📥 Import broker holdings
python run.py --import                   # Import enabled platforms from config.yaml
python run.py --import --platform pko_bp_bonds # Import PKO BP treasury retail bonds
python run.py --import --platform mbank_ike    # Import mBank IKE positions
python run.py --import --platform mbank_ikze   # Import mBank IKZE positions
python run.py --import --platform degiro       # Import Degiro CSV positions
python run.py --import --platform exante       # Import Exante positions (CSV or API)
python run.py --import --api             # Force Exante live REST API mode

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

# 📦 Archive portfolio history (>2yr) and rotate raw broker exports (>1yr)
python run.py --archive

# 🔄 Synchronize & patch downstream personal vault
python run.py --sync-vault ../trader
```

---

## 🔒 Security & Privacy

- Sensitive files such as `.env`, raw broker CSV statements (`00_Raw/*`), and cache files are strictly included in [.gitignore](.gitignore) to prevent accidental credential or personal financial data exposure.
- All broker imports operate locally or through official authenticated REST APIs directly on your machine.

---

## 📄 License

This repository is maintained for private personal portfolio management and financial intelligence.
