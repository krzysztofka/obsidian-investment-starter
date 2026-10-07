---
ticker: V80A_IKZE
name: "Vanguard LifeStrategy 80% Equity UCITS ETF"
platform: mBM
portfolio: Long term
quantity: 85
avg_price: null
current_price: 43.63
value_pln: 16249.75
currency: EUR
asset_type: etf
asset_allocation:
  equity: 80
  bonds: 20
  cash: 0
dominant_sector: Diversified
industry: Diversified
fifty_two_week_high: 26.58
fifty_two_week_low: 26.27
drawdown_52w: "69.06%"
volatility: "9.93%"
sharpe_ratio: 1.19
max_drawdown: "-5.64%"
morningstar_rating: null
morningstar_risk: null
isin: IE00BMVB5R75
yahoo_ticker: V80A.DE
stooq_ticker: v80a.de
issuer: Vanguard
issuer_url: "https://www.de.vanguard/private-anleger/anlageprodukte/etf/multi-asset/9496/lifestrategy-80-equity-ucits-etf-eur-accumulating"
justetf_url: "https://www.justetf.com/en/etf-profile.html?isin=IE00BMVB5R75"
ter: "0.25% p.a."
fund_size: "1,289m Euro"
distribution_policy: Accumulating
replication: Physical
fund_domicile: Ireland
last_updated: "2026-09-16"
source: platform
tags:
  - "#ikze"
---

# Vanguard LifeStrategy 80% Equity UCITS ETF (V80A_IKZE)

**Platform:** [[mBM]]
**JustETF Profile:** [https://www.justetf.com/en/etf-profile.html?isin=IE00BMVB5R75](https://www.justetf.com/en/etf-profile.html?isin=IE00BMVB5R75)
**Issuer Profile:** [https://www.de.vanguard/private-anleger/anlageprodukte/etf/multi-asset/9496/lifestrategy-80-equity-ucits-etf-eur-accumulating](https://www.de.vanguard/private-anleger/anlageprodukte/etf/multi-asset/9496/lifestrategy-80-equity-ucits-etf-eur-accumulating)

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