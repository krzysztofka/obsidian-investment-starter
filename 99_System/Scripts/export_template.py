#!/usr/bin/env python3
"""Export Template Script for Investment Second Brain.

Exports code, templates, dashboards, views, documentation, and a sanitized
sample dataset (including sample raw broker exports and demo portfolio notes)
to a clean standalone template repository (default: ../obsidian-investment-template).
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any

# Resolve current vault root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))


def copy_tree_filtered(src: str, dst: str, ignore_patterns: List[str] = None):
    """Recursively copy directory tree ignoring specified file/folder patterns."""
    if ignore_patterns is None:
        ignore_patterns = ["__pycache__", ".pytest_cache", ".git", ".DS_Store", "*.pyc", "*.log"]

    def _ignore(directory, files):
        ignored = []
        for f in files:
            for pattern in ignore_patterns:
                if pattern.startswith("*") and f.endswith(pattern[1:]):
                    ignored.append(f)
                elif f == pattern:
                    ignored.append(f)
        return set(ignored)

    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if any(item == p or (p.startswith("*") and item.endswith(p[1:])) for p in ignore_patterns):
            continue
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=_ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


def create_sample_raw_files(target_dir: str):
    """Create sanitized sample broker exports in 00_Raw/."""
    raw_dir = os.path.join(target_dir, "00_Raw")
    os.makedirs(os.path.join(raw_dir, "Degiro"), exist_ok=True)
    os.makedirs(os.path.join(raw_dir, "Exante"), exist_ok=True)
    os.makedirs(os.path.join(raw_dir, "mBM"), exist_ok=True)
    os.makedirs(os.path.join(raw_dir, "Articles"), exist_ok=True)

    # 1. Degiro sample CSV
    degiro_sample_path = os.path.join(raw_dir, "Degiro", "sample_degiro.csv")
    degiro_content = """Produkt,Symbol/ISIN,Suma,Kurs,Lokalna wartość,,Wartość w EUR
CASH & CASH FUND & FTX CASH (EUR),,,,EUR,"2500,00","2500,00"
MICROSOFT CORPORATION,US5949181045,10,"420,50",EUR,"4205,00","4205,00"
VANGUARD LIFESTRATEGY 80% EQUITY...,IE00BMVB5R75,100,"43,80",EUR,"4380,00","4380,00"
VANECK DEFENSE UCITS ETF,IE000YYE6WK5,50,"44,20",GBP,"2210,00","2580,00"
KGHM POLSKA MIEDZ SA,PLKGHM000017,50,"350,00",PLN,"17500,00","4050,00"
"""
    with open(degiro_sample_path, "w", encoding="utf-8") as f:
        f.write(degiro_content)

    # 2. Exante sample CSV (UTF-16LE tab-separated)
    exante_sample_path = os.path.join(raw_dir, "Exante", "sample_exante.csv")
    exante_content = """Cash Balances
Instrument\tISO\tValue\tCurrency
EUR Cash\tEUR\t1500.00\tEUR
USD Cash\tUSD\t800.00\tUSD

Stocks & ETFs
Instrument\tName\tQTY\tAvg Price\tPrice\tCurrency\tISIN
MSFT.NASDAQ\tMicrosoft Corporation\t10\t400.00\t420.50\tUSD\tUS5949181045
V80A.XETRA\tVanguard LifeStrategy 80% Equity\t100\t40.00\t43.80\tEUR\tIE00BMVB5R75
"""
    with open(exante_sample_path, "w", encoding="utf-16") as f:
        f.write(exante_content)

    # 3. mBM sample IKE CSV
    mbm_ike_path = os.path.join(raw_dir, "mBM", "sample_ike.csv")
    mbm_ike_content = """mBank S.A. Bankowość Detaliczna
Skrytka Pocztowa 2108
90-959 Łódź 2
www.mBank.pl
mLinia: 801 300 800

eMAKLER - Portfel

#Imię i nazwisko
Sample Investor

#Nr rachunku mBM
99999999

#Nr rachunku powiązanego
#

#Data
16.09.2026



Papier;Giełda;Liczba dostępna (Blokady);Kurs;Waluta;Wartość;Waluta
VWCE GR ETF;DEU-XETRA;30;125,50;EUR;16 189,50;PLN
Łączna wycena papierów
16 189,50
"""
    with open(mbm_ike_path, "w", encoding="utf-8") as f:
        f.write(mbm_ike_content)

    # 4. mBM sample IKZE CSV
    mbm_ikze_path = os.path.join(raw_dir, "mBM", "sample_ikze.csv")
    mbm_ikze_content = """mBank S.A. Bankowość Detaliczna
Skrytka Pocztowa 2108
90-959 Łódź 2
www.mBank.pl
mLinia: 801 300 800

eMAKLER - Portfel

#Imię i nazwisko
Sample Investor

#Nr rachunku mBM
88888888

#Nr rachunku powiązanego
#

#Data
16.09.2026



Papier;Giełda;Liczba dostępna (Blokady);Kurs;Waluta;Wartość;Waluta
V80A GR ETF;DEU-XETRA;85;43,63;EUR;15 978,58;PLN
Łączna wycena papierów
15 978,58
"""
    with open(mbm_ikze_path, "w", encoding="utf-8") as f:
        f.write(mbm_ikze_content)

    # Articles .gitkeep
    with open(os.path.join(raw_dir, "Articles", ".gitkeep"), "w", encoding="utf-8") as f:
        f.write("")


def create_sample_assets(target_dir: str):
    """Create clean demo assets across Safety Net, Long Term, and Aggressive portfolios."""
    assets_dir = os.path.join(target_dir, "10_Finance", "Assets")
    os.makedirs(assets_dir, exist_ok=True)

    sample_assets = [
        # --- Safety Net ---
        ("SAMPLE_BANK_DEPOSIT.md", """---
ticker: SAMPLE_BANK_DEPOSIT
name: Emergency Bank High-Yield Savings
asset_class: cash
currency: PLN
quantity: 50000.0
current_price: 1.0
avg_purchase_price: 1.0
value_pln: 50000.0
portfolio: safety
broker: Bank
source: manual
last_updated: "2026-09-19"
alerts: []
---
# Emergency Bank High-Yield Savings

Primary emergency fund liquidity buffer maintaining 6 months of living expenses.
"""),
        ("SAMPLE_EDO_BOND.md", """---
ticker: SAMPLE_EDO_BOND
name: Polish Retail 10-Year Inflation Bond (EDO)
asset_class: bond
currency: PLN
quantity: 300.0
current_price: 100.0
avg_purchase_price: 100.0
value_pln: 30000.0
portfolio: safety
broker: Treasury Direct
source: manual
last_updated: "2026-09-19"
alerts: []
---
# Polish Retail 10-Year Inflation Bond (EDO)

Inflation-indexed retail sovereign treasury bond guaranteeing capital preservation against domestic CPI inflation.
"""),
        ("DEGIRO_CASH_EUR.md", """---
ticker: DEGIRO_CASH_EUR
name: Degiro Cash Balance (EUR)
asset_class: cash
currency: EUR
quantity: 2500.0
current_price: 1.0
avg_purchase_price: 1.0
value_pln: 10750.0
portfolio: safety
broker: Degiro
source: platform
last_updated: "2026-09-19"
alerts: []
---
# Degiro Cash Balance (EUR)

Unallocated dry powder and settlement cash balance held on Degiro.
"""),

        # --- Long Term ---
        ("IE00BMVB5R75.md", """---
ticker: IE00BMVB5R75
name: Vanguard LifeStrategy 80% Equity UCITS ETF (EUR) Acc
asset_class: etf
currency: EUR
isin: IE00BMVB5R75
yahoo_ticker: V80A.DE
justetf_slug: vanguard-lifestrategy-80-percent-equity-ucits-etf-eur-accumulating
stooq_ticker: v80a.de
quantity: 100.0
current_price: 43.80
avg_purchase_price: 39.50
value_pln: 18834.0
portfolio: long_term
broker: Degiro
source: platform
ter: 0.25
allocation:
  equity: 80.0
  bonds: 20.0
  cash: 0.0
last_updated: "2026-09-19"
alerts: []
---
# Vanguard LifeStrategy 80% Equity UCITS ETF

Core multi-asset global index foundation combining 80% world equity allocation with 20% global sovereign and aggregate fixed income.
"""),
        ("IE00BK5BQT80.md", """---
ticker: IE00BK5BQT80
name: Vanguard FTSE All-World UCITS ETF (USD) Acc
asset_class: etf
currency: EUR
isin: IE00BK5BQT80
yahoo_ticker: VWCE.DE
justetf_slug: vanguard-ftse-all-world-ucits-etf-usd-accumulating
stooq_ticker: vwce.de
quantity: 30.0
current_price: 125.50
avg_purchase_price: 110.00
value_pln: 16189.5
portfolio: long_term
broker: mBM
source: platform
ter: 0.22
allocation:
  equity: 100.0
  bonds: 0.0
  cash: 0.0
last_updated: "2026-09-19"
alerts: []
---
# Vanguard FTSE All-World UCITS ETF

All-cap world equity index tracker providing diversified global equity exposure across developed and emerging economies.
"""),
        ("SAMPLE_PHYSICAL_GOLD.md", """---
ticker: SAMPLE_PHYSICAL_GOLD
name: 1 oz Physical Gold Bullion (Vienna Philharmonic)
asset_class: commodity
currency: PLN
quantity: 1.0
current_price: 10500.0
avg_purchase_price: 8200.0
value_pln: 10500.0
portfolio: long_term
broker: Vault
source: manual
last_updated: "2026-09-19"
alerts: []
---
# 1 oz Physical Gold Bullion

Allocated physical investment gold serving as a sovereign risk hedge and non-correlated currency store of value.
"""),
        ("SAMPLE_REAL_ESTATE.md", """---
ticker: SAMPLE_REAL_ESTATE
name: Investment Studio Apartment
asset_class: real_estate
currency: PLN
quantity: 1.0
current_price: 350000.0
avg_purchase_price: 280000.0
value_pln: 350000.0
portfolio: long_term
broker: Physical
source: manual
last_updated: "2026-09-19"
alerts: []
---
# Investment Studio Apartment

Residential rental property providing defensive positive cash flow and real asset inflation indexing.
"""),

        # --- Aggressive ---
        ("US5949181045.md", """---
ticker: US5949181045
name: Microsoft Corporation
asset_class: equity
currency: USD
isin: US5949181045
yahoo_ticker: MSFT
stooq_ticker: msft.us
quantity: 10.0
current_price: 425.0
avg_purchase_price: 380.0
value_pln: 16575.0
portfolio: aggressive
broker: Degiro
source: platform
sector: Technology
pe_ratio: 35.2
dividend_yield: 0.72
market_cap: 3150000000000
last_updated: "2026-09-19"
alerts: []
---
# Microsoft Corporation

Core enterprise cloud and AI infrastructure provider with compounding high return on invested capital (ROIC).
"""),
        ("IE000YYE6WK5.md", """---
ticker: IE000YYE6WK5
name: VanEck Defense UCITS ETF (USD) Acc
asset_class: etf
currency: GBP
isin: IE000YYE6WK5
yahoo_ticker: DFNS.L
justetf_slug: vaneck-defense-ucits-etf-a
stooq_ticker: dfns.uk
quantity: 50.0
current_price: 44.20
avg_purchase_price: 35.00
value_pln: 11094.0
portfolio: aggressive
broker: Degiro
source: platform
ter: 0.55
allocation:
  equity: 100.0
  bonds: 0.0
  cash: 0.0
last_updated: "2026-09-19"
alerts: []
---
# VanEck Defense UCITS ETF

Thematic exposure to global defense industry contractors, aerospace systems, and cybersecurity infrastructure.
"""),
        ("PLKGHM000017.md", """---
ticker: PLKGHM000017
name: KGHM Polska Miedz SA
asset_class: equity
currency: PLN
isin: PLKGHM000017
yahoo_ticker: KGH.WA
stooq_ticker: kgh.pl
quantity: 50.0
current_price: 350.0
avg_purchase_price: 210.0
value_pln: 17500.0
portfolio: aggressive
broker: Degiro
source: platform
sector: Basic Materials
pe_ratio: 14.5
dividend_yield: 2.1
market_cap: 70000000000
last_updated: "2026-09-19"
alerts: []
---
# KGHM Polska Miedz SA

Cyclical copper and silver producer benefiting from global electrification and grid infrastructure demand.
"""),
    ]

    for filename, content in sample_assets:
        filepath = os.path.join(assets_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")


def create_sample_etf_holdings(target_dir: str):
    """Create sample ETF decomposed top holdings."""
    holdings_dir = os.path.join(target_dir, "10_Finance", "ETF_Holdings")
    os.makedirs(holdings_dir, exist_ok=True)

    overview_content = """# 🔬 ETF Underlying Holdings Overview

Deconstructed look-through exposures across all portfolio ETFs.

```dataview
TABLE
  holding_name AS "Company",
  round(sum_exposure_pln, 2) AS "Total Exposure (PLN)",
  sector AS "Sector",
  country AS "Country",
  round(avg_weight_pct, 2) AS "Avg Weight %",
  length(in_etfs) AS "ETFs Count"
FROM "10_Finance/ETF_Holdings"
WHERE file.name != "Holdings_Overview"
SORT sum_exposure_pln DESC
```
"""
    with open(os.path.join(holdings_dir, "Holdings_Overview.md"), "w", encoding="utf-8") as f:
        f.write(overview_content)

    sample_holdings = [
        ("MSFT.md", """---
ticker: MSFT
holding_name: Microsoft Corp.
sector: Technology
country: United States
in_etfs:
  - "[[10_Finance/Assets/IE00BMVB5R75|Vanguard LifeStrategy 80%]]"
  - "[[10_Finance/Assets/IE00BK5BQT80|Vanguard FTSE All-World]]"
sum_exposure_pln: 1250.40
avg_weight_pct: 3.85
direct_position_pln: 16575.00
total_combined_pln: 17825.40
---
# Microsoft Corp. (Underlying Holding)
"""),
        ("AAPL.md", """---
ticker: AAPL
holding_name: Apple Inc.
sector: Technology
country: United States
in_etfs:
  - "[[10_Finance/Assets/IE00BMVB5R75|Vanguard LifeStrategy 80%]]"
  - "[[10_Finance/Assets/IE00BK5BQT80|Vanguard FTSE All-World]]"
sum_exposure_pln: 1180.20
avg_weight_pct: 3.60
direct_position_pln: 0.00
total_combined_pln: 1180.20
---
# Apple Inc. (Underlying Holding)
"""),
        ("NVDA.md", """---
ticker: NVDA
holding_name: NVIDIA Corporation
sector: Technology
country: United States
in_etfs:
  - "[[10_Finance/Assets/IE00BMVB5R75|Vanguard LifeStrategy 80%]]"
  - "[[10_Finance/Assets/IE00BK5BQT80|Vanguard FTSE All-World]]"
sum_exposure_pln: 940.80
avg_weight_pct: 2.90
direct_position_pln: 0.00
total_combined_pln: 940.80
---
# NVIDIA Corporation (Underlying Holding)
"""),
        ("RHM.DE.md", """---
ticker: RHM.DE
holding_name: Rheinmetall AG
sector: Industrials
country: Germany
in_etfs:
  - "[[10_Finance/Assets/IE000YYE6WK5|VanEck Defense UCITS ETF]]"
sum_exposure_pln: 980.50
avg_weight_pct: 8.84
direct_position_pln: 0.00
total_combined_pln: 980.50
---
# Rheinmetall AG (Underlying Holding)
"""),
    ]

    for filename, content in sample_holdings:
        filepath = os.path.join(holdings_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")


def create_sample_history(target_dir: str):
    """Create sample portfolio history timeline."""
    history_dir = os.path.join(target_dir, "10_Finance", "History")
    os.makedirs(history_dir, exist_ok=True)

    history_csv_path = os.path.join(history_dir, "portfolio.csv")
    history_content = """date,total_value_pln,invested_capital_pln,profit_pln,return_pct
2026-06-01,480000.00,450000.00,30000.00,6.67
2026-07-01,495000.00,455000.00,40000.00,8.79
2026-08-01,510000.00,460000.00,50000.00,10.87
2026-09-01,525000.00,465000.00,60000.00,12.90
2026-09-19,534898.50,465000.00,69898.50,15.03
"""
    with open(history_csv_path, "w", encoding="utf-8") as f:
        f.write(history_content.strip() + "\n")


def create_sample_decisions(target_dir: str):
    """Create sample decision thesis and retrospective notes."""
    dec_dir = os.path.join(target_dir, "20_Decisions", "2026")
    os.makedirs(dec_dir, exist_ok=True)

    decision_path = os.path.join(dec_dir, "2026-09-01_MSFT_BUY.md")
    decision_content = """---
ticker: MSFT
action: BUY
portfolio: aggressive
status: active
date: "2026-09-01"
quantity: 10
execution_price: 420.50
currency: USD
broker: Degiro
tags:
  - decision/active
  - asset/equity
---

# Investment Decision: MSFT (BUY)

## 🎯 Context & Thesis
- **Catalyst:** Azure cloud revenue acceleration and commercial Copilot monetization.
- **Horizon:** 3-5 years compounder.
- **Exit Target:** $550+ or fundamental deceleration in cloud growth below 15%.

## 🛡️ Pre-Mortem Analysis
- **Failure Mode:** AI infrastructure overcapacity leading to margin compression.
- **Mitigation:** Position size capped at max 8% of total liquid portfolio.
"""
    with open(decision_path, "w", encoding="utf-8") as f:
        f.write(decision_content.strip() + "\n")

    retrospective_path = os.path.join(target_dir, "20_Decisions", "2026-Q3_Retrospective.md")
    retrospective_content = """---
period: 2026-Q3
date: "2026-09-19"
type: quarterly_retrospective
tags:
  - retrospective/quarterly
---

# 2026 Q3 Investment Retrospective

## 📊 Summary of Decisions
- **Total Executed Trades:** 3
- **Adherence to Silo Rule:** 100%
- **Key Realizations:** Rebalanced defensive cash cushions and initiated tax-advantaged IKE allocations.

## 💡 Key Lessons
1. Systematic monthly contributions consistently outperform market timing.
2. Maintaining strict cash safety cushions eliminated emotional reactions during short-term market pullbacks.
"""
    with open(retrospective_path, "w", encoding="utf-8") as f:
        f.write(retrospective_content.strip() + "\n")


def create_template_gitignore(target_dir: str):
    """Create template-specific .gitignore that allows 00_Raw sample files."""
    gitignore_path = os.path.join(target_dir, ".gitignore")
    content = """# ==============================================================================
# Obsidian Investment Template - Git Ignore Configuration
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Environment Variables & Secret API Keys (CRITICAL)
# ------------------------------------------------------------------------------
.env
.env.*
!.env.example
*.key
*.pem
*.pfx

# ------------------------------------------------------------------------------
# 2. Raw Broker Data Exports
# In the template repository, sample raw files in 00_Raw are tracked.
# To keep personal data private, ignore custom CSVs by uncommenting below:
# ------------------------------------------------------------------------------
# 00_Raw/*
# !00_Raw/Articles/
# !00_Raw/**/sample_*.csv
# !00_Raw/**/.gitkeep

# ------------------------------------------------------------------------------
# 3. Python Runtime & Virtual Environments
# ------------------------------------------------------------------------------
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
venv/
.venv/
env/
ENV/
env.bak/
venv.bak/
.cache/
**/.cache/

# ------------------------------------------------------------------------------
# 4. Logs & Operational Artifacts
# ------------------------------------------------------------------------------
*.log
99_System/runner.log
99_System/Scripts/*.log

# ------------------------------------------------------------------------------
# 5. Obsidian Workspace Sessions & Local App State
# ------------------------------------------------------------------------------
.obsidian/workspace*
.obsidian/graph.json
.obsidian/starred.json
.obsidian/backlink.json
.obsidian/cache
.obsidian/.trash/
.trash/

# ------------------------------------------------------------------------------
# 6. Operating System & IDE Cache Files
# ------------------------------------------------------------------------------
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
desktop.ini
$RECYCLE.BIN/
.idea/
.vscode/
*.swp
*.swo
*~
"""
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


def create_template_env_example(target_dir: str):
    """Create .env.example with documented credentials."""
    env_example_path = os.path.join(target_dir, ".env.example")
    content = """# ==============================================================================
# Obsidian Investment Brain - Environment Variables Template
# Copy this file to .env and fill in your actual credentials.
# ==============================================================================

# 1. Finnhub API (Analyst Consensus Ratings & SEC Insider Trading Alerts)
# Get a free key at: https://finnhub.io/
FINNHUB_API_KEY=your_finnhub_api_key_here

# 2. Exante REST API (Live Position & Multi-Currency Balance Synchronization)
# Obtain Application ID & Shared Key from Exante Client Portal
EXANTE_API_KEY=your_exante_application_id
EXANTE_API_SECRET=your_exante_shared_key
EXANTE_ACCOUNT_ID=your_exante_account_id_optional
EXANTE_API_URL=https://api-live.exante.eu
"""
    with open(env_example_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


def create_mit_license(target_dir: str):
    """Create MIT License file for the public template."""
    license_path = os.path.join(target_dir, "LICENSE")
    current_year = datetime.now().year
    content = f"""MIT License

Copyright (c) {current_year} Obsidian Investment Brain

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    with open(license_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


def export_template(
    target_dir: Optional[str] = None,
    init_git: bool = True,
) -> str:
    """Execute full template export pipeline."""
    if not target_dir:
        # Default to ../obsidian-investment-template
        target_dir = os.path.abspath(os.path.join(VAULT_ROOT, "..", "obsidian-investment-template"))

    print(f"🚀 Exporting Obsidian Investment Template...")
    print(f"   Source Vault : {VAULT_ROOT}")
    print(f"   Target Dir   : {target_dir}")

    os.makedirs(target_dir, exist_ok=True)

    # 1. Copy core system folder (Scripts, Templates, Views, config.yaml)
    print("📦 Copying system automation suite, templates & UI views...")
    copy_tree_filtered(
        os.path.join(VAULT_ROOT, "99_System", "Scripts"),
        os.path.join(target_dir, "99_System", "Scripts"),
    )
    copy_tree_filtered(
        os.path.join(VAULT_ROOT, "99_System", "Templates"),
        os.path.join(target_dir, "99_System", "Templates"),
    )
    copy_tree_filtered(
        os.path.join(VAULT_ROOT, "99_System", "Views"),
        os.path.join(target_dir, "99_System", "Views"),
    )
    if os.path.exists(os.path.join(VAULT_ROOT, "99_System", "config.yaml")):
        shutil.copy2(
            os.path.join(VAULT_ROOT, "99_System", "config.yaml"),
            os.path.join(target_dir, "99_System", "config.yaml"),
        )

    # 2. Copy root configuration & runner files
    for filename in ["run.py", "config.yaml", "README.md", "GEMINI.md", "todo.md"]:
        src_file = os.path.join(VAULT_ROOT, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(target_dir, filename))

    # 3. Copy root dashboards
    for dashboard in [
        "Overview.md",
        "Safety_portfolio.md",
        "Long_term_portfolio.md",
        "Aggressive_portfolio.md",
        "Portfolio_performance.md",
        "Alerts.md",
        "Welcome.md",
    ]:
        src_file = os.path.join(VAULT_ROOT, dashboard)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(target_dir, dashboard))

    # 4. Copy 10_Finance static dashboards & watchlists
    os.makedirs(os.path.join(target_dir, "10_Finance"), exist_ok=True)
    if os.path.exists(os.path.join(VAULT_ROOT, "10_Finance", "Macro.md")):
        shutil.copy2(
            os.path.join(VAULT_ROOT, "10_Finance", "Macro.md"),
            os.path.join(target_dir, "10_Finance", "Macro.md"),
        )
    if os.path.exists(os.path.join(VAULT_ROOT, "10_Finance", "Watchlist")):
        copy_tree_filtered(
            os.path.join(VAULT_ROOT, "10_Finance", "Watchlist"),
            os.path.join(target_dir, "10_Finance", "Watchlist"),
        )

    # 5. Copy .obsidian plugins & configuration (excluding session workspace)
    if os.path.exists(os.path.join(VAULT_ROOT, ".obsidian")):
        print("⚙️ Copying Obsidian community plugins & vault settings...")
        copy_tree_filtered(
            os.path.join(VAULT_ROOT, ".obsidian"),
            os.path.join(target_dir, ".obsidian"),
            ignore_patterns=["workspace*", "cache", "starred.json", ".trash"],
        )

    # 6. Generate sample raw files (00_Raw/)
    print("📁 Generating sample raw broker exports in 00_Raw/...")
    create_sample_raw_files(target_dir)

    # 7. Generate sample portfolio asset notes (10_Finance/Assets/)
    print("💼 Generating sample portfolio asset notes...")
    create_sample_assets(target_dir)

    # 8. Generate sample ETF holdings (10_Finance/ETF_Holdings/)
    print("🔬 Generating sample ETF look-through holdings...")
    create_sample_etf_holdings(target_dir)

    # 9. Generate sample history timeline (10_Finance/History/portfolio.csv)
    print("📈 Generating sample portfolio historical timeline...")
    create_sample_history(target_dir)

    # 10. Generate sample decisions & retrospectives (20_Decisions/)
    print("🧠 Generating sample investment decisions & retrospectives...")
    create_sample_decisions(target_dir)

    # 11. Create template configuration & license files
    print("📄 Creating .gitignore, .env.example, and LICENSE...")
    create_template_gitignore(target_dir)
    create_template_env_example(target_dir)
    create_mit_license(target_dir)

    # 12. Optional git initialization
    if init_git:
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            print("🔧 Initializing Git repository in template directory...")
            try:
                subprocess.run(["git", "init"], cwd=target_dir, check=True, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=target_dir, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "feat: initial commit of obsidian-investment-template"],
                    cwd=target_dir,
                    check=True,
                    capture_output=True,
                )
                print("   Git repository successfully initialized.")
            except Exception as e:
                print(f"   Note: Git init skipped or had warning: {e}")

    print(f"\n✅ Template export successfully completed: {target_dir}")
    return target_dir


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    export_template(target_dir=target)
