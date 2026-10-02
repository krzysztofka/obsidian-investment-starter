---
# === 1. Core Position ===
ticker: AAPL
name: Apple Inc.
platform: Degiro
portfolio: "Aggressive"  # Options: "Safety net", "Long term", "Aggressive"
quantity: 15
avg_price: 150.50
current_price: 175.20
value_pln: 10512.00
currency: USD
asset_type: equity       # Options: "equity", "etf", "cash"
asset_allocation:
  equity: 100

# === 2. Structure & Allocation ===
dominant_sector: Technology
industry: Technology
sector: Technology
country: United States

# === 3. Valuation & Fundamentals ===
market_cap: 3.40T
pe_ratio: 36.29
forward_pe: 33.22
dividend_yield: 0.50%

# === 4. Technicals & Momentum ===
fifty_two_week_high: 344.57
fifty_two_week_low: 225.95
drawdown_52w: -8.04%
sma_50: 312.0
sma_200: 282.6
rsi_14: 56.26
beta: 1.09

# === 5. Quantitative & Risk (OpenBB / Morningstar) ===
volatility: null
sharpe_ratio: null
max_drawdown: null
upside_potential: null
morningstar_rating: null
morningstar_risk: null
analyst_rating: Buy

# === 6. ETF Specifics & Market Identifiers (if applicable) ===
isin: null
yahoo_ticker: AAPL
stooq_ticker: aapl.us       # e.g. "aapl.us" (US), "kgh" (GPW), "v80a.de" (UCITS), "xauusd" (Gold), "10ply.b" (Bonds)
issuer: null             # e.g. "iShares", "Vanguard", "VanEck", "SPDR", "Invesco", "Amundi", "Xtrackers"
issuer_url: null
justetf_url: null
ter: null
fund_size: null
distribution_policy: null
replication: null
fund_domicile: null
top_holdings: []

# === 7. Meta & Alerts ===
last_updated: 2026-08-31
source: platform         # Options: "platform", "manual"
tags: []
---

# Apple Inc. (AAPL)

**Platform:** [[Degiro]]

> [!INFO] **Key Metrics Snapshot**
> | Metric | Value | Metric | Value |
> | :--- | :--- | :--- | :--- |
> | **P/E (Trailing / Forward)** | `= this.pe_ratio` / `= this.forward_pe` | **52w Range** | `= this.fifty_two_week_low` - `= this.fifty_two_week_high` |
> | **Drawdown from 52w High** | `= this.drawdown_52w` | **Trend (SMA 200)** | `= this.sma_200` |
> | **RSI (14)** | `= this.rsi_14` | **Beta** | `= this.beta` |
> | **Dividend Yield** | `= this.dividend_yield` | **Market Cap** | `= this.market_cap` |

## 📈 Technical & Market Price Chart
```dataviewjs
await dv.view("99_System/Views/stooq_chart", {
    ticker: dv.current().stooq_ticker,
    height: 480
});
```

## 💡 Investment Thesis
*Why does this asset exist in this portfolio? What is the core catalyst or multi-year compounding mechanism?*

## ⚠️ Pre-Mortem & Risks
*If this investment fails, what was the most likely reason? What risks are we accepting?*

## 🎯 Exit Strategy & Key Triggers
- **Target Valuation / Exit:** 
- **Invalidation Trigger (When to sell):** 
- **Stop Loss / Allocation Cap:** 

## 📝 Trade Logs & Decisions
```dataview
TABLE file.link AS "Decision", date AS "Date", type AS "Action", price AS "Price"
FROM "20_Decisions"
WHERE contains(file.name, this.ticker) OR contains(file.name, this.file.name)
SORT date DESC
```