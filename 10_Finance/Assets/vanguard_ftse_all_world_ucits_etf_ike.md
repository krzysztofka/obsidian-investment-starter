---
ticker: VWCE_IKE
name: "Vanguard FTSE All-World UCITS ETF"
platform: mBM
portfolio: Long term
quantity: 30
avg_price: null
current_price: 125.5
value_pln: 16497.1
currency: EUR
asset_type: etf
asset_allocation:
  equity: 100
dominant_sector: Diversified
industry: Diversified
pe_ratio: 21.02
fifty_two_week_high: 202.3
fifty_two_week_low: 140.22
drawdown_52w: "-4.18%"
sma_50: 192.85
sma_200: 182.5
rsi_14: 52.42
volatility: "11.78%"
sharpe_ratio: 1.39
max_drawdown: "-6.55%"
morningstar_rating: null
morningstar_risk: null
isin: IE00BK5BQT80
yahoo_ticker: VWCE.DE
stooq_ticker: vwra.uk
issuer: Vanguard
issuer_url: "https://www.de.vanguard/private-anleger/anlageprodukte/etf/aktien/9679/ftse-all-world-ucits-etf-usd-accumulating"
justetf_url: "https://www.justetf.com/en/etf-profile.html?isin=IE00BK5BQT80"
ter: "0.14% p.a."
fund_size: "54,126m Euro"
distribution_policy: Accumulating
replication: Physical
fund_domicile: Ireland
last_updated: "2026-09-16"
source: platform
tags:
  - "#ike"
---

# Vanguard FTSE All-World UCITS ETF (VWCE_IKE)

**Platform:** [[mBM]]
**JustETF Profile:** [https://www.justetf.com/en/etf-profile.html?isin=IE00BK5BQT80](https://www.justetf.com/en/etf-profile.html?isin=IE00BK5BQT80)
**Issuer Profile:** [https://www.de.vanguard/private-anleger/anlageprodukte/etf/aktien/9679/ftse-all-world-ucits-etf-usd-accumulating](https://www.de.vanguard/private-anleger/anlageprodukte/etf/aktien/9679/ftse-all-world-ucits-etf-usd-accumulating)

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