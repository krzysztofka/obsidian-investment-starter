---
type: macro_dashboard
title: Global & Domestic Macroeconomic Dashboard
last_updated: "2026-09-29"
us_10y_yield: 5.24
us_2y_yield: 4.50
yield_spread_10y_2y_bps: 74.0
yield_curve_status: "Normal (Upward Sloping)"
pl_10y_yield: 5.81
nbp_reference_rate: 3.75
poland_cpi: 2.5
usd_pln: 3.8478
eur_pln: 4.3769
gbp_pln: 5.1054
gold_usd: 4172.20
gold_pln: 15944.89
silver_usd: 61.12
copper_usd: 6.59
brent_usd: 98.51
vix: 16.10
macro_regime: "Steep Curve / Mid-Cycle Expansion"
tags:
  - macro
  - finance
  - intelligence
---

# 🌐 Macroeconomic Dashboard & Market Regime

A central tracking hub for global and domestic macroeconomic indicators, monetary policy, and interest rate environments to guide asset allocation, risk management, and portfolio silo decisions.

> 🧭 **Related Dashboards:** [[Overview|📊 Main Overview]] · [[Safety_portfolio|🛡️ Safety Net]] · [[Long_term_portfolio|🏛️ Long Term]] · [[Aggressive_portfolio|🚀 Aggressive]] · [[Alerts|🚨 Active Alerts]]

---

## 🏛️ Central Bank Interest Rates & Monetary Policy

| Central Bank | Benchmark Rate | Current Level | Trend / Bias | Last Decision Date | Next Decision Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Federal Reserve (Fed)** | Fed Funds Target Range | 4.75% – 5.00% | Neutral / Easing | 2026-07-29 | 2026-09-16 |
| **European Central Bank (ECB)** | Main Refinancing / Deposit Rate | 3.25% / 3.00% | Easing | 2026-07-18 | 2026-09-10 |
| **National Bank of Poland (NBP)** | Stopa Referencyjna | 3.75% | Easing / Cut | 2026-03-05 | 2026-10-07 |


---

## 📊 Inflation & Labor Market Indicators

| Indicator | Region | Current (YoY / %) | Prior Period | Target / Benchmark | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CPI Inflation** | 🇺🇸 United States | 2.6% | 2.8% | 2.0% | Moderating |
| **HICP Inflation** | 🇪🇺 Eurozone | 2.0% | 2.1% | 2.0% | Moderating |
| **CPI / HICP Inflation** | 🇵🇱 Poland | 2.5% | 2.6% | 2.5% (±1.0%) | Moderating |
| **Unemployment Rate** | 🇺🇸 United States | 4.1% | 4.0% | ~4.0% (Full Employment) | Stable |
| **Unemployment Rate (Eurostat/BAEL)** | 🇵🇱 Poland | 3.4% – 5.0% | 5.0% | Historical Low Range | Strong |


---

## 📈 Yield Curves & Fixed Income Spreads

| Metric / Benchmark | Ticker / Source | Current Yield / Spread | 1M Trend | Signal / Implication |
| :--- | :--- | :--- | :--- | :--- |
| **US 10-Year Treasury** | `^TNX` | 5.24% | 📈 Increasing | Benchmark cost of capital; valuation hurdle |
| **US 2-Year Treasury** | `2YY=F` / `^IRX` | 4.50% | 📈 Increasing | Policy expectations & short-term rate path |
| **10Y – 2Y Treasury Spread** | Calculated Spread | **+74 bps (+0.74%)** | ➡️ Normal (Upward Sloping) | Yield curve term premia & cycle position |
| **Poland 10-Year Bond (DS)** | `PL10Y` (Eurostat) | 5.81% | 📈 Increasing | High domestic nominal yield, attractive real returns |

---

## ⛏️ Strategic Commodities & Cyclicals

| Commodity | Ticker | Current Price | 52-Week Range | Impact on Portfolio Assets |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Gold (USD / oz)** | `GC=F` | $4,172 | $3,786 – $5,586 | Safe-haven hedge in [[Long_term_portfolio\|Long Term]] (`GOLD`) |
| **Gold (PLN / oz)** | NBP Fixing | 15,945 PLN | NBP Domestic Price | Domestic purchasing power & currency debasement hedge |
| **Silver (USD / oz)** | `SI=F` | $61.12 | $45.38 – $121.30 | Revenue driver for [[PLKGHM000017\|KGHM Polska Miedź]] |
| **Copper (USD / lb)** | `HG=F` | $6.59 | $4.71 – $6.83 | Global bellwether & core EBITDA driver for [[PLKGHM000017\|KGHM]] |
| **Brent Crude Oil** | `BZ=F` | $98.51 | $58.72 – $126.10 | Wholesale costs & refining margin indicator for [[PLPKN0000018\|ORLEN]] |

---

## 🌪️ Market Volatility & Sentiment

| Metric | Ticker | Current Level | Regime / Status | Strategic Implication |
| :--- | :--- | :--- | :--- | :--- |
| **CBOE Volatility Index (VIX)** | `^VIX` | 16.10 | Complacent / Low Volatility | Equity fear gauge; risk-on entry signal for [[Aggressive_portfolio\|Aggressive]] |

---

## 💱 Key Currencies

| Asset | Ticker | Current Level | 52-Week Range | Strategic Impact |
| :--- | :--- | :--- | :--- | :--- |
| **USD/PLN** | `USDPLN=X` / NBP | 3.8478 PLN | 3.49 – 3.86 | FX conversion rate for US holdings & USD tech equities |
| **EUR/PLN** | `EURPLN=X` / NBP | 4.3769 PLN | 4.19 – 4.40 | Eurozone export & cash cushion valuation |
| **GBP/PLN** | `GBPPLN=X` / NBP | 5.1054 PLN | 4.77 – 5.11 | Valuation multiplier for [[vaneck_defense_ucits_etf\|VanEck Defense ETF (LSE)]] |

---

## 🧭 Current Macro Regime & Portfolio Implications

```
   ┌────────────────────────────────────────────────────────┐
   │ Current Regime: Steep Curve / Mid-Cycle Expansion      │
   │ Positive term premia and healthy economic expansion with accommodative policy. │
   └────────────────────────────────────────────────────────┘
```

### 🛡️ Safety Net Portfolio
- **Retail Treasury Bonds (EDO/ROD):** Inflation-indexed bonds offer high guaranteed real yields (CPI + margin), securing purchasing power without volatility.
- **Cash Buffers:** High nominal short-term deposit rates in PLN remain attractive, but cash yields will gradually decline as rate cuts unfold.

### 🏛️ Long Term Portfolio
- **Broad Equities & Core ETFs:** Stabilizing interest rates support multi-decade equity compounding.
- **Fixed Income & Sovereign Bonds:** Potential duration capital gains as global yields decline from cyclical highs.
- **Physical Gold:** Continues to provide structural geopolitical and sovereign debt debasement protection.

### 🚀 Aggressive Portfolio
- **High-Beta & Growth Equities:** Declining risk-free discount rates support valuations for tech and cyclical growth assets.
- **Commodity & Cyclical Exposure:** Copper and silver price momentum directly benefits KGHM, while refining margins drive Orlen.
- **Selectivity:** High real interest rates still challenge heavily indebted and unprofitable small-cap companies; focus remains on profitable cash-generative leaders.

---

## 📝 Observations & Macro Thesis Log

### 2026-09-03: Yield Curve Normalization & Monetary Easing Cycle
- The US 10Y-2Y yield curve has normalized out of inversion, reflecting anticipated rate cuts by the Federal Reserve and ECB.
- Polish inflation remains sticky around 4.3%, keeping the NBP on hold longer than Western central banks, supporting the Polish Zloty (PLN) strength against USD and EUR.
- *Action Plan:* Maintain full emergency liquidity in Polish inflation-indexed retail bonds and EUR/PLN buffers; continue dollar-cost averaging into core global ETFs.
