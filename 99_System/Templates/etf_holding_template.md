---
ticker: {{ticker}}
name: {{name}}
asset_type: etf_holding
dominant_sector: {{dominant_sector}}
sector: {{sector}}
industry: {{industry}}
country: {{country}}
market_cap: {{market_cap}}
pe_ratio: {{pe_ratio}}
dividend_yield: {{dividend_yield}}
current_price: {{current_price}}
currency: {{currency}}
parent_etfs:
  - "[[{{parent_etf}}]]"
total_indirect_value_pln: {{total_indirect_value_pln}}
direct_asset: {{direct_asset}}
last_updated: "{{date}}"
tags:
  - etf_holding
---

# {{name}} ({{ticker}})

**Direct Holding in Portfolio:** {{direct_holding_badge}}  
**Sector:** {{sector}} | **Industry:** {{industry}} | **Country:** {{country}}  
**Market Cap:** {{market_cap}} | **P/E Ratio:** {{pe_ratio}} | **Dividend Yield:** {{dividend_yield}}

---

## 📊 ETF Exposure & Weight
| ETF | ETF Name | Holding Weight (%) | Indirect Value (PLN) |
| --- | --- | --- | --- |
{{etf_exposure_rows}}

## 💡 Notes & Analysis
Information about reasoning for tracking and analyzing this holding.
