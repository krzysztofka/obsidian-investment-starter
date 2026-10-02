---
type: macro_dashboard
title: Global & Domestic Macroeconomic Dashboard
last_updated: "{{ last_updated }}"
us_10y_yield: {{ "%.2f"|format(us_10y_yield) }}
us_2y_yield: {{ "%.2f"|format(us_2y_yield) }}
yield_spread_10y_2y_bps: {{ yield_spread_10y_2y_bps }}
yield_curve_status: "{{ yield_curve_status }}"
pl_10y_yield: {{ "%.2f"|format(pl_10y_yield) }}
nbp_reference_rate: {{ "%.2f"|format(nbp_reference_rate) }}
poland_cpi: {{ "%.1f"|format(poland_cpi) }}
usd_pln: {{ "%.4f"|format(usd_pln) }}
eur_pln: {{ "%.4f"|format(eur_pln) }}
gbp_pln: {{ "%.4f"|format(gbp_pln) }}
gold_usd: {{ "%.2f"|format(gold_usd) }}
gold_pln: {{ "%.2f"|format(gold_pln) }}
silver_usd: {{ "%.2f"|format(silver_usd) }}
copper_usd: {{ "%.2f"|format(copper_usd) }}
brent_usd: {{ "%.2f"|format(brent_usd) }}
vix: {{ "%.2f"|format(vix) }}
macro_regime: "{{ macro_regime_title }}"
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
{% for cb in central_banks -%}
| {{ cb.name }} | {{ cb.rate }} | {{ cb.level }} | {{ cb.trend }} | {{ cb.last_date }} | {{ cb.next_date }} |
{% endfor %}

---

## 📊 Inflation & Labor Market Indicators

| Indicator | Region | Current (YoY / %) | Prior Period | Target / Benchmark | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
{% for inf in inflation -%}
| {{ inf.indicator }} | {{ inf.region }} | {{ inf.current }} | {{ inf.prior }} | {{ inf.target }} | {{ inf.status }} |
{% endfor %}

---

## 📈 Yield Curves & Fixed Income Spreads

| Metric / Benchmark | Ticker / Source | Current Yield / Spread | 1M Trend | Signal / Implication |
| :--- | :--- | :--- | :--- | :--- |
| **US 10-Year Treasury** | `^TNX` | {{ "%.2f"|format(us_10y_yield) }}% | {{ us_10y_trend }} | Benchmark cost of capital; valuation hurdle |
| **US 2-Year Treasury** | `2YY=F` / `^IRX` | {{ "%.2f"|format(us_2y_yield) }}% | {{ us_2y_trend }} | Policy expectations & short-term rate path |
| **10Y – 2Y Treasury Spread** | Calculated Spread | {{ spread_display }} | ➡️ {{ yield_curve_status }} | Yield curve term premia & cycle position |
| **Poland 10-Year Bond (DS)** | `PL10Y` (Eurostat) | {{ "%.2f"|format(pl_10y_yield) }}% | {{ pl_10y_trend }} | High domestic nominal yield, attractive real returns |

---

## ⛏️ Strategic Commodities & Cyclicals

| Commodity | Ticker | Current Price | 52-Week Range | Impact on Portfolio Assets |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Gold (USD / oz)** | `GC=F` | ${{ "{:,.0f}".format(gold_usd) }} | {{ gold_range }} | Safe-haven hedge in [[Long_term_portfolio\|Long Term]] (`GOLD`) |
| **Gold (PLN / oz)** | NBP Fixing | {{ "{:,.0f}".format(gold_pln) }} PLN | NBP Domestic Price | Domestic purchasing power & currency debasement hedge |
| **Silver (USD / oz)** | `SI=F` | ${{ "%.2f"|format(silver_usd) }} | {{ silver_range }} | Revenue driver for [[PLKGHM000017\|KGHM Polska Miedź]] |
| **Copper (USD / lb)** | `HG=F` | ${{ "%.2f"|format(copper_usd) }} | {{ copper_range }} | Global bellwether & core EBITDA driver for [[PLKGHM000017\|KGHM]] |
| **Brent Crude Oil** | `BZ=F` | ${{ "%.2f"|format(brent_usd) }} | {{ brent_range }} | Wholesale costs & refining margin indicator for [[PLPKN0000018\|ORLEN]] |

---

## 🌪️ Market Volatility & Sentiment

| Metric | Ticker | Current Level | Regime / Status | Strategic Implication |
| :--- | :--- | :--- | :--- | :--- |
| **CBOE Volatility Index (VIX)** | `^VIX` | {{ "%.2f"|format(vix) }} | {{ vix_status }} | Equity fear gauge; risk-on entry signal for [[Aggressive_portfolio\|Aggressive]] |

---

## 💱 Key Currencies

| Asset | Ticker | Current Level | 52-Week Range | Strategic Impact |
| :--- | :--- | :--- | :--- | :--- |
| **USD/PLN** | `USDPLN=X` / NBP | {{ "%.4f"|format(usd_pln) }} PLN | {{ usd_pln_range }} | FX conversion rate for US holdings & USD tech equities |
| **EUR/PLN** | `EURPLN=X` / NBP | {{ "%.4f"|format(eur_pln) }} PLN | {{ eur_pln_range }} | Eurozone export & cash cushion valuation |
| **GBP/PLN** | `GBPPLN=X` / NBP | {{ "%.4f"|format(gbp_pln) }} PLN | {{ gbp_pln_range }} | Valuation multiplier for [[vaneck_defense_ucits_etf\|VanEck Defense ETF (LSE)]] |

---

## 🧭 Current Macro Regime & Portfolio Implications

```
   ┌────────────────────────────────────────────────────────┐
   │ Current Regime: {{ "%-38s"|format(macro_regime_title) }} │
   │ {{ "%-54s"|format(macro_regime_desc) }} │
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

{{ custom_notes_section }}
